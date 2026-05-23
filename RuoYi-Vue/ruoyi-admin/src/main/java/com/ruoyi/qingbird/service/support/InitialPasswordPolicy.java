package com.ruoyi.qingbird.service.support;

import java.util.Set;

/**
 * Shared initial password strength checks for Qingbird account creation.
 */
public final class InitialPasswordPolicy {
    private static final Set<String> WEAK_PASSWORDS = Set.of(
            "123456",
            "admin123",
            "password",
            "111111",
            "000000"
    );

    private InitialPasswordPolicy() {
    }

    public static boolean isWeak(String password) {
        String value = password == null ? "" : password.trim().toLowerCase();
        return WEAK_PASSWORDS.contains(value);
    }
}
