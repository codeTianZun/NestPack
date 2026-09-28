# MP4 视频融合与原归档提取

## 选择操作

| 目标 | 入口 | 结果 |
|---|---|---|
| 新建归档时为某层融合视频 | `--layer-video` / `--layer-source-video`，或 `layers[].disguise` | 本层一个 MP4，下一层包裹该文件 |
| 为已有归档融合视频 | `--fuse-archive ARCHIVE --video MP4` | 一个 MP4，归档内容与密码保持原样 |
| 从融合文件取回压缩包 | `--extract-video-archive MP4` | 原格式归档，提取时校验 SHA256 |
| 直接恢复归档中的文件 | `--unpack MP4` | 逐层解包后的载荷，见 [unpack.md](unpack.md) |

融合与提取本身不需要归档密码或外部归档工具；创建压缩层与解包仍需要
相应工具和密码。融合不增加压缩层数，`--layers` 计算实际归档层数。

## 逐层视频与来源映射

在项目根目录运行（Windows 将 `python3` 换成 `python`）：

```bash
python3 -m cli --source ./data --output ./out --layer 7z --layer-name inner --layer-video ./cover.mp4 --layer zip --layer-name outer --yes --non-interactive --json
```

此任务先得到 `inner.mp4`，再包入 `outer.zip`。每层独立选择载体，交付文件
读取成功结果的 `groups[].final`。默认自检后删除中间层。

分别打包时为某个来源选专用视频：

```bash
python3 -m cli --source ./data/a --source ./data/b --output ./out --compress-mode separate --layer 7z --layer-video ./cover.mp4 --layer-source-video ./data/b ./b-cover.mp4 --yes --non-interactive --json
```

JSON 对应字段为本层的 `disguise`：

```json
{
  "mode": "video",
  "extension": ".bin",
  "video_path": "cover.mp4",
  "source_video_paths": {"data/b": "b-cover.mp4"}
}
```

分别打包按解析后的来源路径匹配专用视频，未指定的来源使用本层默认视频；
所有来源都有专用视频时可以不填默认值。合并打包使用本层默认视频。
配置中来源映射的键、值和默认视频都相对配置目录；直接 CLI 参数相对调用目录。
`--layer-disguise video` 显式选择方式；`--layer-video` 和
`--layer-source-video` 也会启用视频方式，显式 `--layer-disguise` 优先。

任务级 `--video`、`--source-video`、`--video-fusion` / `--no-video-fusion`
用于设置最外层，见 [cli.md](cli.md)。新配置统一写逐层 `disguise`。

视频层使用完整的普通单文件归档：`volume_size=null`、`sfx.enabled=false`。
其他层可以分卷或自解压；需要融合已有分卷或 SFX 时，先将它们包入一个
普通单文件外层。外层归档需包含该套的全部分卷。

## 独立融合与提取

```bash
python3 -m cli --fuse-archive ./existing.zip --video ./cover.mp4 --output ./fused --non-interactive --json
python3 -m cli --extract-video-archive ./fused/existing.mp4 --output ./restored --non-interactive --json
```

两种模式的 `--output` 都是目录，缺省为调用目录。融合输出名为
`原归档主名.mp4`，提取输出名为 `融合文件主名.原归档格式`；提取恢复原始字节，
文件名按融合文件主名生成。成功结果的 `mode` 分别为 `video_fusion` 和
`video_extract`，`files` 包含实际产物路径。

独立模式接收对应输入、融合所需的 `--video`、`--output`、
`--overwrite-existing` 及通用展示参数；压缩配置、层参数、密码、工具路径和
`--dry-run` 属于其他模式。提取输入必须含 NestPack 融合记录。
覆盖同名目标使用 `--overwrite-existing`，源视频与归档保持完整。
任务支持取消，临时文件在结束时清理，成功后发布目标文件。

## 载体与交付

- 选择包含完整媒体数据的普通或分片 MP4，保留原画面、声音和编码。
  已有 NestPack 融合归档的视频不能再次用作载体；每层使用原始载体文件。
- 引用外部媒体、压缩 QuickTime 索引或含加密辅助偏移的载体会报转换提示，
  按提示先另存为普通独立 MP4。
- 本地播放器打开 MP4；外部解压软件能否直接打开同一文件，按对应环境确认。
  RAR / 7z 融合文件可能提示归档尾部存在额外数据，同时核实校验或解包结果。
- 网盘预览取决于服务端解析。交付验证分别检查在线播放和下载原文件后的
  提取、解包；云端转码的视频不能作为原归档恢复输入。当前已验证环境见
  项目 `使用说明.md` 的「视频融合」，不要把本地成功等同于云端兼容。

实现依据：`cli/video_cmd.py`、
`core/video/fusion.py`、`core/video/mp4.py`、`core/video/zip_directory.py`、
`core/compression/planning.py`、`core/unpack/workflow.py`。
