# Selenium配置说明

## 概述

为了支持JavaScript动态加载的网页（如CSDN搜索结果页面），系统现在支持使用Selenium进行网页爬取。

## 安装要求

### 1. 安装Python包
```bash
pip install selenium
```

### 2. 安装WebDriver

根据你使用的浏览器，需要下载对应的WebDriver：

#### Chrome浏览器
1. 查看Chrome版本：在浏览器地址栏输入 `chrome://version/`
2. 下载对应版本的ChromeDriver：https://chromedriver.chromium.org/
3. 将ChromeDriver放在系统PATH中，或指定路径

#### Edge浏览器
1. 查看Edge版本：在浏览器地址栏输入 `edge://version/`
2. 下载对应版本的EdgeDriver：https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
3. 将EdgeDriver放在系统PATH中，或指定路径

#### Firefox浏览器
1. 下载GeckoDriver：https://github.com/mozilla/geckodriver/releases
2. 将GeckoDriver放在系统PATH中，或指定路径

**注意**：Selenium 4.6+版本支持自动管理WebDriver，如果未指定路径，会自动下载。

## 配置采集源

在创建或更新采集源时，可以在爬虫配置中启用Selenium：

```json
{
  "use_selenium": true,
  "selenium_config": {
    "browser": "chrome",
    "headless": true,
    "wait_timeout": 15,
    "driver_path": "C:/path/to/chromedriver.exe",
    "content_wait_selector": ".article-content, .post-content, article, main",
    "scroll_to_load": true,
    "extra_wait_time": 2
  },
  "search_wait_selector": ".search-list-con"
}
```

### 配置参数说明

- **use_selenium**: `true` 或 `false`，是否使用Selenium模式
- **selenium_config**:
  - **browser**: 浏览器类型，可选值：`chrome`、`edge`、`firefox`（默认：`chrome`）
  - **headless**: 是否无头模式运行（默认：`true`）
  - **wait_timeout**: 等待页面加载的超时时间（秒，默认：15）
  - **driver_path**: WebDriver可执行文件的路径（可选，默认使用系统PATH）
  - **content_wait_selector**: 等待内容元素出现的CSS选择器（可选，支持多个用逗号分隔，如：`.article-content, article`）。系统会等待这些元素出现后再提取内容，确保JavaScript动态内容完全加载
  - **scroll_to_load**: 是否滚动页面触发懒加载内容（默认：`true`）。设置为`true`时，系统会滚动到底部再回到顶部，触发懒加载的内容
  - **extra_wait_time**: 额外等待时间（秒，默认：2）。在页面加载和滚动后，额外等待的时间，确保动态内容完全渲染
- **search_wait_selector**: 搜索模式下，等待搜索结果出现的CSS选择器（可选）

## 完整文字内容爬取配置示例

为了确保完整爬取JavaScript动态加载的文字内容，推荐使用以下配置：

```json
{
  "use_selenium": true,
  "selenium_config": {
    "browser": "chrome",
    "headless": true,
    "wait_timeout": 20,
    "content_wait_selector": ".article-content, .post-content, article, main",
    "scroll_to_load": true,
    "extra_wait_time": 2
  },
  "selectors": {
    "content": ".article-content",
    "title": "h1"
  }
}
```

### 配置说明

1. **启用Selenium**: `use_selenium: true`
2. **内容等待选择器**: `content_wait_selector` 指定页面主要内容的选择器，系统会等待这些元素出现后再提取，确保动态内容加载完成
3. **滚动触发懒加载**: `scroll_to_load: true` 自动滚动页面触发懒加载内容
4. **额外等待时间**: `extra_wait_time: 2` 在等待和滚动后额外等待2秒，确保所有内容渲染完成

## CSDN搜索结果配置示例

对于CSDN搜索，推荐配置：

```json
{
  "use_selenium": true,
  "selenium_config": {
    "browser": "chrome",
    "headless": true,
    "wait_timeout": 20,
    "scroll_to_load": true,
    "extra_wait_time": 3
  },
  "selectors": {
    "search_result_link": ".search-list-con .search-item h3 a"
  },
  "search_wait_selector": ".search-list-con"
}
```

### 配置说明

1. **启用Selenium**: `use_selenium: true`
2. **等待选择器**: `search_wait_selector: ".search-list-con"` 确保搜索结果容器加载完成后再提取链接
3. **结果链接选择器**: `selectors.search_result_link` 指定CSDN搜索结果中的文章链接选择器
4. **滚动触发懒加载**: `scroll_to_load: true` 滚动页面以加载更多搜索结果

## 使用步骤

1. **安装Selenium和WebDriver**（见上）
2. **创建采集源时**，在"爬虫配置"字段中输入JSON配置（启用Selenium）
3. **配置搜索参数**，例如：`{"q": "Python"}`
4. **触发采集**，系统会使用Selenium加载页面并提取结果

## 智能等待机制

系统实现了智能等待机制，确保JavaScript动态内容完全加载：

1. **文档就绪检查**: 等待`document.readyState`为`complete`
2. **Body元素等待**: 等待body元素出现
3. **内容元素等待**: 如果配置了`content_wait_selector`，等待指定的内容元素出现
4. **网络空闲检查**: 检查页面网络请求是否完成
5. **额外等待时间**: 根据`extra_wait_time`配置，额外等待一段时间

这些机制确保页面完全加载后再提取内容，提高内容提取的完整性。

## 滚动触发懒加载

当`scroll_to_load`设置为`true`时，系统会：

1. 滚动到页面底部
2. 等待新内容加载
3. 如果页面高度增加，继续滚动（最多3次）
4. 最后滚动回顶部

这样可以触发页面的懒加载机制，确保所有动态内容都被加载。

## 内容提取增强

系统改进了内容提取机制：

1. **多策略提取**: 尝试多种常见的内容容器选择器
2. **智能选择**: 自动选择包含最多文字内容的容器
3. **内容验证**: 验证提取的内容是否包含足够的文字
4. **清理无关内容**: 自动移除导航、广告、评论等无关内容

## 注意事项

1. Selenium模式比普通requests模式慢，因为需要启动浏览器
2. 确保系统有足够的资源运行浏览器（特别是内存）
3. 首次使用可能需要下载WebDriver（如果使用自动管理）
4. 如果遇到问题，检查日志中的错误信息
5. 对于复杂页面，适当增加`wait_timeout`和`extra_wait_time`
6. 配置`content_wait_selector`可以显著提高内容提取的成功率和完整性

## 故障排查

### WebDriver未找到
- 确保WebDriver已安装并在PATH中
- 或指定完整的`driver_path`

### 页面加载超时
- 增加`wait_timeout`值
- 检查网络连接
- 确认目标网站可访问

### 无法提取链接
- 检查`search_wait_selector`是否正确
- 验证页面结构是否改变
- 查看调试HTML文件（保存在`logs/debug_html/`）

### 内容提取不完整
- 配置`content_wait_selector`指定页面主要内容的选择器
- 启用`scroll_to_load`以触发懒加载内容
- 增加`extra_wait_time`给页面更多渲染时间
- 检查页面是否使用了特殊的内容加载机制（如无限滚动）

### 页面加载缓慢
- 适当增加`wait_timeout`（但不要设置过长，避免长时间等待）
- 检查网络连接
- 考虑使用`headless: true`（无头模式通常更快）
