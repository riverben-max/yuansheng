package com.ruoyi.qingbird.config;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import com.ruoyi.common.utils.StringUtils;

/**
 * Fails fast with a clear message when required deployment variables are absent.
 */
@Component
public class RequiredEnvironmentValidator implements ApplicationRunner {
    private static final String[] REQUIRED_KEYS = {
            "DB_USERNAME",
            "DB_PASSWORD",
            "RUOYI_TOKEN_SECRET"
    };

    private final Environment environment;

    public RequiredEnvironmentValidator(Environment environment) {
        this.environment = environment;
    }

    @Override
    public void run(ApplicationArguments args) {
        List<String> missingKeys = new ArrayList<>();
        for (String key : REQUIRED_KEYS) {
            if (StringUtils.isBlank(environment.getProperty(key))) {
                missingKeys.add(key);
            }
        }
        if (!missingKeys.isEmpty()) {
            throw new IllegalStateException("Missing required environment variables: "
                    + String.join(", ", missingKeys)
                    + ". Example: DB_USERNAME=ruoyi DB_PASSWORD=change-me RUOYI_TOKEN_SECRET=replace-with-long-random-secret");
        }
    }
}
