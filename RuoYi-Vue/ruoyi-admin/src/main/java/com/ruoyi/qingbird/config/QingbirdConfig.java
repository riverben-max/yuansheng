package com.ruoyi.qingbird.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import com.ruoyi.qingbird.interceptor.SignatureInterceptor;

@Configuration
public class QingbirdConfig implements WebMvcConfigurer {

    @Autowired
    private SignatureInterceptor signatureInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // Register the SignatureInterceptor for RPA upload paths
        registry.addInterceptor(signatureInterceptor).addPathPatterns("/spider/**");
    }
}
