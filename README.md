## 有哪些模块？

1. 聊天对话（`chat/`）
2. 做题判题（`judge/`）
3. 题目和题目集的设计（`design/`）
4. 作业的布置（`assign/`）
5. pdf文档的上传和阅读（`pdf/`）

## 这些模块之间的关系？

模块的依赖关系如下：

![模块依赖图](docs\img\module_dependency.png)

## 数据库里有哪些表？

数据库的ER图如下：

![数据库ER图](docs\img\database_ER.png)

## 有调用什么外部API吗？

大语言模型的API，调用的是[智谱](https://www.bigmodel.cn/)的，用的SDK是OpenAI的。

OJ判题机，用的是青岛大学开源的[JudgeServer](https://github.com/QingdaoU/JudgeServer)，直接通过Docker镜像部署在我的Linux云服务器上了。
