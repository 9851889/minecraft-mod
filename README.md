# 星辉兽 StarBeast

> 一个 Minecraft Java 版 **1.20.4** 自定义生物模组 —— 学习记录。

在这个仓库里我会一步步把「星辉兽」做出来：先是能召唤的实体，再是看得见的模型，然后是会动的 AI，最后打包成能装进游戏的成品。

---

## 产品展示

<p align="center">
  <img src="docs/flying-shoe-poster.png" alt="飞行鞋 展示封面" width="620">
</p>

<p align="center">
  <video src="docs/flying-shoe.mp4" autoplay loop muted playsinline width="620"></video>
</p>

<p align="center">
  <a href="docs/flying-shoe.mp4">📥 MP4 视频</a> ·
  <a href="docs/flying-shoe.webp">轻量动图 WebP</a> ·
  <a href="docs/flying-shoe.gif">GIF</a> ·
  <a href="docs/make_showcase_video.py">渲染脚本</a>
</p>

| 能力 | 说明 |
|:--|:--|
| **穿上即起飞** | 装备到靴子槽，羽翼自动展开，无需潜行或烟花 |
| **鞘翅式滑翔** | 空中按住前进键加速，俯仰角决定滑翔方向 |
| **落地无摔伤** | 滑翔状态下完全免疫坠落伤害，血量不掉 |

> 这段片子演示的是项目**调整后的方向**——从「会飞的四足生物」改为「可装备的飞行鞋」。
> 视频里的靴子和游戏内使用的是**同一套 16×16 像素美术**（`docs/make_showcase_video.py` 可以重新生成整段片子）。

---

## 技术栈

| 项 | 选型 | 说明 |
|---|---|---|
| Minecraft | **1.20.4** | 已装客户端，直接在本机测试 |
| 模组加载器 | **Fabric** | Loom `1.19-SNAPSHOT` + Loader `0.20.1` + Fabric API `0.97.3+1.20.4` |
| 映射 | **Mojang 官方映射** | 类名方法名与官方 Wiki 一致，查资料方便 |
| 语言 / 字节码 | **Java 17** | 1.20.4 的要求 |
| 构建工具 | Gradle 9.8.2（Loom 插件） | 用 Gradle 包装器，**无需单独安装 Gradle** |

---

## 环境准备（已完成）

| 组件 | 位置 | 备注 |
|---|---|---|
| JDK 25 | `C:\Users\<你的用户名>\.jdks\jdk-25` | **只给 Gradle/Loom 用**（Loom 1.19 字节码要求 JVM 25+） |
| JDK 17 | `C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot` | **编译与运行游戏用**，系统自带 |
| JDK 21 | `C:\Users\<你的用户名>\.jdks\jdk-21` | 备用 |
| Gradle 缓存 | `C:\Users\<你的用户名>\.gradle` | 标准位置，在 VS Code 里构建时直接复用 |

### 两个必须知道的坑

**1️⃣ 加速器根证书**

本机装了 Steam++ (Watt Toolkit) 加速器，它会做 TLS 中间人。Windows 信任它的根证书，所以 `git`/`curl` 正常；但 **Java 用自己的 cacerts，不认 Windows 证书库**，导致 Gradle 下载依赖时：

```
PKIX path building failed: unable to find valid certification path to requested target
```

**解决办法**（已执行）：把根证书导入 JDK 的信任库。

```powershell
# 导出 SteamTools Certificate（LocalMachine\Root 与 CurrentUser\Root 各一份）
# 再导入到 JDK 21/25 的 cacerts
keytool -importcert -noprompt -alias steamtools-root -file steamtools.cer `
        -keystore "C:\Users\<你的用户名>\.jdks\jdk-25\lib\security\cacerts" -storepass changeit
```

**2️⃣ 沙箱会让 `Files.isWritable()` 误报为 false**

Loom 拆分 Minecraft jar 时，用 `Files.isWritable()` 判断能否写入新 jar。DSH 沙箱的受限令牌会让它返回 false，于是拿到只读句柄：

```
java.nio.file.ReadOnlyFileSystemException
    at net.fabricmc.loom...MinecraftJarSplitter.copyEntriesToJar
```

**解决办法**：**Gradle 构建必须在沙箱外执行**（与 `git push` 同理）。在 VS Code 终端里直接跑则完全没有这个问题。

---

## 目录结构

```
minecraft-mod/
├── gradle.properties        # 所有版本号和 JDK 路径集中在这里
├── build.gradle             # Loom 插件配置、依赖、Java 工具链
├── settings.gradle          # 仓库源（含阿里云/腾讯镜像加速）
├── gradlew / gradlew.bat    # Gradle 包装器
└── src/
    ├── main/java/com/example/starbeast/
    │   └── StarBeastMod.java          # 模组主入口
    ├── main/resources/
    │   └── fabric.mod.json            # 模组元数据
    ├── client/java/com/example/starbeast/client/
    │   └── StarBeastClient.java       # 客户端入口（模型/渲染器注册）
    └── client/resources/               # 客户端资源（模型 JSON、贴图、语言文件）
```

> `splitEnvironmentSourceSets()` 把 `src/main`（通用）和 `src/client`（纯客户端）拆开了。
> 渲染相关的类**只能**放在 `src/client`，否则专用服务端会崩。

---

## 常用命令

在工程根目录（`minecraft-mod/`）执行：

```powershell
# 编译打包 -> build/libs/starbeast-1.0.0.jar
.\gradlew.bat build

# 直接启动开发客户端（自带我们的模组，改代码后 F5 重启即可生效）
.\gradlew.bat runClient

# 只重编译
.\gradlew.bat classes
```

> `runClient` 会在 `minecraft-mod/run/` 生成一个独立的开发存档，
> **不会动你 `.minecraft` 里的正式存档**。

---

## 开发进度

| 步骤 | 内容 | 状态 |
|:--:|---|:--:|
| 1 | 安装 JDK 21 / 25，打通 TLS 信任 | ✅ |
| 2 | 搭建 Fabric 工程（1.20.4），构建出 jar | ✅ |
| 3 | 跑通 `runClient`，启动开发客户端 | ⬜ |
| 4 | 生物实体类 + 注册（类型/属性/刷怪蛋） | ⬜ |
| 5 | 客户端渲染（模型 + 渲染器 + 贴图） | ⬜ |
| 6 | AI 行为（目标 + 移动） | ⬜ |
| 7 | 语言文件 + 刷怪配置 | ⬜ |
| 8 | 打包 jar → PCL 里实测 | ⬜ |

---

## 参考资料

- [Fabric 开发者文档](https://docs.fabricmc.net/develop/)
- [Fabric Wiki（中文）](https://wiki.fabricmc.net/zh/)
- [mappings.dev（查 Mojang 映射）](https://mappings.dev/1.20.4/net/minecraft/world/entity/Mob.html)
- [Minecraft Wiki（中文）](https://zh.minecraft.wiki/)
- [Fabric API 文档](https://maven.fabricmc.net/docs/fabric-api-0.97.3+1.20.4/)
