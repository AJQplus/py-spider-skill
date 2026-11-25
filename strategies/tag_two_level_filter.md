# 标签站二级分类筛选体系策略模块 v9.5

## 适用特征

- 站点无传统 MacCMS 分类树，内容组织靠**标签制**：列表页 `/s/{tag}/`，组合标签 `/s/{tag1}+{tag2}/`（URL 空格即 `+`）。
- 首页/分类页有官方 **Top Tags / 热门标签** 区块，标签间无显式主次层级。
- 用户要求"分类有主次、做成二级分类和筛选"。
- 典型站点：spankbang.com（/s/{tag}/ 标签制）、同类 tube 站。

## 核心流程

### 1. 提取官方标签（以官网真实数据为准，禁止凭空编）

从首页/`/categories` 页抓官方 **Top Tags 精选区块**的标签链接（`href="/s/{tag}/"`），去重后得到候选集：
- 剔除**纯演员名标签**（与内容分类无关，点进去是同一批片）。
- 全量标签过多（90+）时按热度和覆盖面**精选 25~35 个顶级分类**——顶级分类要求内容互斥度高（实测两两对比重复率），避免用户"每个分类内容都一样"的观感。

### 2. 固定推荐区与真实列表分离（铁律）

tube 站分类页顶部普遍有 **6~10 个固定推荐视频**（所有分类页都相同的 id）。列表提取必须：
- 定位真实列表容器（如最后一个 `data-testid="video-list"`），只取容器内节点；
- 或按 video id 去重后对比分类间差异，若重叠率 100% 说明混入了推荐区。
- 用两个差异大的分类实测对比（如 amateur vs blowjob），重叠必须为 0。

### 3. 二级筛选构建（filters 挂子标签）

从真实分类页抓**相关子标签区块**（如 `searched-for-item`），为每个顶级分类取前 10 个子标签构建 filters：

```python
self.filters = {
    "japanese": [{"key": "sub", "name": "子分类", "value": [
        {"n": "Blowjob", "v": "blowjob"}, {"n": "Asian", "v": "asian"}, ...
    ]}],
    ...
}
```

categoryContent 拼接规则：子分类非空时 `tag = tid + "+" + sub`，URL `/s/{tag}/{page}`（`+` 需 quote）：

```python
tag = (tid + "+" + sub) if sub else tid
url = self.host + "/s/" + quote(tag.replace(" ", "+")) + "/" + page
```

- extend 兼容四形态：dict / JSON 字符串 / 空串 / None，`sub` 取不到就当无筛选。
- 组合标签 URL 实测验证（如 `japanese+blowjob` 条数应与单标签不同）。

### 4. 域名与韧性

- 域名池探活（主域 + www 子域/备用域），探活判据含真实列表特征。
- `_get` 3 次重试 + 退避；单条解析异常 continue。

## 验证门禁

- 分类间内容互斥：任取两个顶级分类第一页，重复 id 数为 0。
- 二级筛选生效：`categoryContent(tid, 1, True, {"sub": xxx})` 返回条数/内容与主分类不同。
- 分页真实：pagecount 从页面分页链接解析，翻页内容有变化。

## 案例参考

- SpankBang（v9.4）：官网 Top Tags 98 个 → 剔 6 个演员名 → 90 全量 → 精选 30 顶级 + 30 组 filters（每挂 10 子标签）；固定推荐 8 条混淆修复后 amateur vs blowjob 重叠 100%→0。
