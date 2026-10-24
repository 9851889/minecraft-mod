package com.example.starbeast;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 星辉兽模组 —— 主入口。
 *
 * <p>Fabric 模组在启动时会给每个 {@code main} 入口点调用一次 {@link #onInitialize()}，
 * 这是所有注册逻辑（方块、物品、生物实体……）的起点。</p>
 *
 * <p>注意：这里只能放「服务端和客户端都要执行」的代码。
 * 渲染、贴图、按键这类纯客户端的东西要放到
 * {@code src/client/java/.../client/StarBeastClient.java} 里。</p>
 */
public class StarBeastMod implements ModInitializer {

	/** 模组 ID，必须和 fabric.mod.json 里的 "id" 一致。 */
	public static final String MOD_ID = "starbeast";

	/** 日志记录器，游戏日志里搜 MOD_ID 就能找到我们的输出。 */
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		LOGGER.info("[{}] 星辉兽模组已加载！", MOD_ID);
	}
}
