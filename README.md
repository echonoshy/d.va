# d.va
> D.Va拥有一部强大的机甲，它具有两台全自动的近距离聚变机炮、可以使机甲飞跃敌人或障碍物的推进器、 还有可以抵御来自正面的远程攻击的防御矩阵

—— From [OverWatch](http://ow.blizzard.cn/heroes/dva)

<img src="https://zos.alipayobjects.com/rmsportal/psagSCVHOKQVqqNjjMdf.jpg" width="200" height="200" />

## 项目简介

D.VA 是一个基于大模型优化的端到端多人TTS引擎，专注于播客节目创作。项目的目标是让AI辅助创作变得简单而有趣。

https://github.com/user-attachments/assets/703eddfa-f641-4a23-b54f-c666a9263709

### 音频示例
[ai_podcast.webm](https://github.com/user-attachments/assets/a64f099a-7455-4142-af2f-0b68cb7e0679)
> 提示：如果无法在线播放，请[点击下载](assets/ai_podcast_v1.MP3)


### 项目配置

#### 1. 模型下载
从Hugging Face下载预训练模型:
```bash
cd models/
git lfs install
git clone https://huggingface.co/echonoshy/d.va
```

#### 2. 第三方库
```bash
apt install ffmpeg rubberband-cli
```

#### 3. pip库
```bash
pip install -r requirements.txt
```


### 项目启动
在.env 文件中增加硅基流动deepseek api-key, 字段名为：SILICONFLOW_API_KEY

```bash
python launch.py # 启动本地tts服务
python webui.py  # 启动web界面
```


## 应用场景

构建一个可以每日更新语音版新闻的助手，然后自动推送到播客和小红书涨粉。


### 实现路径
1. 每日获取不同领域的专业新闻
2. 讲新闻分解成新闻稿
3. 新闻稿变成语音稿件 （带片头片尾曲，时长不超过4分钟）
4. 自动推送到小红书和播客

## 新特性TODO:
1. 增加声音克隆功能
2. 增加自定义音色
3. 解决api访问较慢问题
4. 增加其他场景功能（待定）
