# flexget-plugins
一些flexget插件，目前有：
  - [豆瓣过滤插件](#豆瓣过滤插件)

# 豆瓣过滤插件

## 免责声明
本插件会爬取details.php页面，请将参数限制到合理的范围，减轻对服务器负担<br>
本插件已尽量减轻服务器负担，因本插件造成账号封禁等损失，请自行承担后果<br>
**建议** 将RSS条目限制在20条以内，将Flexget运行频率设置在10分钟以上。
如果不想对人数进行过滤，不建议设置seeders和leechers参数。<br>

## 安装插件
1. 下载插件 [douban.py](https://github.com/leishi1313/flexget-plugins/blob/main/douban.py)
2. 在Flexget配置文件夹下新建plugins文件夹，例如：
```
~/.flexget/plugins/  # Linux
C:\Users\<YOURUSER>\flexget\plugins\  # Windows
```
再次注意`plugins`文件夹和`config.yml`处在同一级目录下，例如：
```
/.flxget
  ┕━config.yml
  ┕━plugins
    ┕━douban.py
```
3. 将插件拷贝至plugins
4. 若启用了Web-UI或守护进程，则重启flexget重新加载配置

## 使用
1. 编辑flexget配置文件，添加nexusphp选项，按照需要进行配置

### 最简配置（筛选豆瓣7分以上资源）
```yaml
douban:
  ptgen: https://ptgen.xxx.xxx.xxx  # PTGen地址，必填
  cookie: 'a=xxx; b=xxx' # 必填
  score: 7 # 豆瓣评分，选填
```

### 多项筛选项配置（筛选豆瓣7分以上诺兰烧脑动作片）
```yaml
douban:
  ptgen: https://ptgen.xxx.xxx.xxx  # PTGen地址，必填
  cookie: 'a=xxx; b=xxx' # 选填
  score: 7 # 豆瓣评分，选填
  director:
    - Christopher Nolan
  genre:
    - 动作
  tags:
    - 烧脑
```

### 完整配置
```yaml
douban:
  ptgen: https://ptgen.xxx.xxx.xxx  # PTGen地址，必填
  cookie: 'a=xxx; b=xxx' # 选填
  score: 7 # 豆瓣评分，选填
  director: # 豆瓣导演信息，选填，建议使用英文
    - XXXX
  cast: # 豆瓣演员信息，选填，建议使用英文
    - XXXX
  writer: # 豆瓣导演信息，选填，建议使用英文
    - XXXX
  genre: # 豆瓣类型信息，选填
    - 动作
  language: # 豆瓣语言信息，选填
    - 英语
  region: # 豆瓣地区信息，选填
    - 美国
  tags: # 豆瓣成员常用的标签，选填
    - 烧脑
```

# Thanks
- [flexget-nexusphp](https://github.com/Juszoe/flexget-nexusphp)