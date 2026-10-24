package com.example.starbeast.client;

import net.fabricmc.api.ClientModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 星辉兽模组 —— 客户端入口。
 *
 * <p>由 {@code build.gradle} 里的 {@code splitEnvironmentSourceSets()} 拆出来的独立源集，
 * 只有在真正启动客户端时才会执行，所以可以安全地引用渲染相关的类。</p>
 *
 * <p>生物的模型和渲染器会注册在这里。</p>
 */
public class StarBeastClient implements ClientModInitializer {

	private static final Logger LOGGER = LoggerFactory.getLogger("starbeast-client");

	@Override
	public void onInitializeClient() {
		LOGGER.info("[starbeast] 客户端入口已加载，等待注册星辉兽的模型与渲染器……");
	}
}
