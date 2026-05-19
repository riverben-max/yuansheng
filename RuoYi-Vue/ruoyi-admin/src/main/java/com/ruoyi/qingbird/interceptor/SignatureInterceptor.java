package com.ruoyi.qingbird.interceptor;

import java.io.PrintWriter;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import com.alibaba.fastjson2.JSON;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.sign.Md5Utils;

/**
 * 自动化采集上传接口防伪造签名拦截器
 */
@Component
public class SignatureInterceptor implements HandlerInterceptor {
    private static final Logger log = LoggerFactory.getLogger(SignatureInterceptor.class);

    @Value("${qingbird.rpa.app-key:QINGBIRD_RPA_01}")
    private String appKey;

    @Value("${qingbird.rpa.secret-key:8c7v6b5n4m3,2.1/}")
    private String secretKey;

    @Value("${qingbird.rpa.ttl-seconds:300}")
    private int ttlSeconds;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        
        // Only intercept /spider/ paths
        String path = request.getRequestURI();
        if (!path.contains("/spider/")) {
            return true;
        }

        String appKey = request.getHeader("X-App-Key");
        String timestamp = request.getHeader("X-Timestamp");
        String sign = request.getHeader("X-Sign");

        if (appKey == null || timestamp == null || sign == null) {
            return returnErrorResponse(response, "Missing signature headers (X-App-Key, X-Timestamp, X-Sign)");
        }

        if (!this.appKey.equals(appKey)) {
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

        // Expected Sign = MD5(APP_KEY + timestamp + SECRET_KEY)
        String expectedSign = Md5Utils.hash(this.appKey + timestamp + this.secretKey);

        if (!expectedSign.equalsIgnoreCase(sign)) {
            log.warn("Invalid signature. Expected: {}, Got: {}", expectedSign, sign);
            return returnErrorResponse(response, "Invalid Signature");
        }

        return true;
    }

    private boolean returnErrorResponse(HttpServletResponse response, String message) throws Exception {
        response.setContentType("application/json");
        response.setCharacterEncoding("utf-8");
        PrintWriter writer = response.getWriter();
        writer.print(JSON.toJSONString(AjaxResult.error(401, message)));
        writer.close();
        return false;
    }
}
