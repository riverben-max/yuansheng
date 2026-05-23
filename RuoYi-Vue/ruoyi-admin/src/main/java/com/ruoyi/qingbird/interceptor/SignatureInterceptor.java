package com.ruoyi.qingbird.interceptor;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import com.alibaba.fastjson2.JSON;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.http.HttpHelper;

/**
 * 自动化采集上传接口防伪造签名拦截器
 */
@Component
public class SignatureInterceptor implements HandlerInterceptor {
    private static final Logger log = LoggerFactory.getLogger(SignatureInterceptor.class);

    @Value("${qingbird.rpa.app-key:}")
    private String appKey;

    @Value("${qingbird.rpa.secret-key:}")
    private String secretKey;

    @Value("${qingbird.rpa.ttl-seconds:300}")
    private int ttlSeconds;

    private final ConcurrentHashMap<String, Long> replayCache = new ConcurrentHashMap<>();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        
        // Only intercept /spider/ paths
        String path = request.getRequestURI();
        if (!path.contains("/spider/")) {
            return true;
        }

        String appKey = request.getHeader("X-App-Key");
        String timestamp = request.getHeader("X-Timestamp");
        String requestId = request.getHeader("X-Request-Id");
        String nonce = request.getHeader("X-Nonce");
        String bodyHash = request.getHeader("X-Body-SHA256");
        String sign = request.getHeader("X-Sign");

        if (isBlank(this.appKey) || isBlank(this.secretKey)) {
            return returnErrorResponse(response, "RPA signature config missing");
        }

        if (appKey == null || timestamp == null || requestId == null || nonce == null || bodyHash == null || sign == null) {
            return returnErrorResponse(response, "Missing signature headers (X-App-Key, X-Timestamp, X-Request-Id, X-Nonce, X-Body-SHA256, X-Sign)");
        }

        if (isBlank(requestId) || isBlank(nonce)) {
            return returnErrorResponse(response, "Invalid replay protection headers");
        }

        String configuredAppKey = this.appKey.trim();
        String configuredSecretKey = this.secretKey.trim();

        if (!configuredAppKey.equals(appKey)) {
            return returnErrorResponse(response, "Invalid App-Key");
        }

        // Validate timestamp (protect against replay attacks)
        long currentSeconds = System.currentTimeMillis() / 1000;
        long reqSeconds = 0;
        try {
            reqSeconds = Long.parseLong(timestamp);
        } catch (NumberFormatException e) {
            return returnErrorResponse(response, "Invalid Timestamp Format");
        }

        if (Math.abs(currentSeconds - reqSeconds) > this.ttlSeconds) {
            return returnErrorResponse(response, "Request expired or timestamp invalid");
        }

        String body = HttpHelper.getBodyString(request);
        String expectedBodyHash = sha256Hex(body);
        if (!MessageDigest.isEqual(expectedBodyHash.getBytes(StandardCharsets.UTF_8), bodyHash.getBytes(StandardCharsets.UTF_8))) {
            return returnErrorResponse(response, "Invalid Body Hash");
        }

        String signPayload = configuredAppKey + "\n" + timestamp + "\n" + requestId + "\n" + nonce + "\n" + normalizedPath(request) + "\n" + expectedBodyHash;
        String expectedSign = hmacSha256Hex(configuredSecretKey, signPayload);
        if (!MessageDigest.isEqual(expectedSign.getBytes(StandardCharsets.UTF_8), sign.toLowerCase().getBytes(StandardCharsets.UTF_8))) {
            log.warn("Invalid signature for appKey: {}", appKey);
            return returnErrorResponse(response, "Invalid Signature");
        }

        if (isReplay(configuredAppKey, requestId, nonce, currentSeconds)) {
            return returnErrorResponse(response, "Replay request rejected");
        }

        return true;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String normalizedPath(HttpServletRequest request) {
        String uri = request.getRequestURI();
        String contextPath = request.getContextPath();
        if (!isBlank(contextPath) && uri.startsWith(contextPath)) {
            return uri.substring(contextPath.length());
        }
        return uri;
    }

    private String sha256Hex(String value) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return toHex(digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8)));
    }

    private String hmacSha256Hex(String secret, String value) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return toHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
    }

    private boolean isReplay(String appKey, String requestId, String nonce, long currentSeconds) {
        cleanupReplayCache(currentSeconds);
        String replayKey = appKey + ":" + requestId + ":" + nonce;
        Long expiresAt = currentSeconds + Math.max(1, this.ttlSeconds);
        return replayCache.putIfAbsent(replayKey, expiresAt) != null;
    }

    private void cleanupReplayCache(long currentSeconds) {
        Iterator<Map.Entry<String, Long>> iterator = replayCache.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, Long> entry = iterator.next();
            if (entry.getValue() < currentSeconds) {
                replayCache.remove(entry.getKey(), entry.getValue());
            }
        }
    }

    private String toHex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            builder.append(String.format("%02x", b));
        }
        return builder.toString();
    }

    private boolean returnErrorResponse(HttpServletResponse response, String message) throws Exception {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.setCharacterEncoding("utf-8");
        PrintWriter writer = response.getWriter();
        writer.print(JSON.toJSONString(AjaxResult.error(401, message)));
        writer.close();
        return false;
    }
}
