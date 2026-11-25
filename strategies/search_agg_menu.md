# 搜索设置伪分类与聚合搜索模块 v9.5
TVBox 没有原生 checkbox。用「伪分类 + folder 按钮 + 编码 vod_id + 状态变量 + 确认卡」模拟设置菜单。
## 适用特征
- 需要给用户切换：搜索站点（单站/多站组合/全站聚合）、并发页码、排序、是否去重等。
- 搜索副标题需要标注来源与页码。
- 参考实现：404 自动挡（自研聚合源 42 站）、花都自动挡（苹果CMS 15 线路）。
## 1. 状态骨架（init 变量）
| 变量 | 默认 | 含义 |
|---|---|---|
| `_search_tid` | `"cangku"` | 单搜站源 type_id |
| `_search_name` | `"仓库"` | 单搜站源中文名（副标题用） |
| `_search_mode` | `"single"` | `single`(单搜)/`agg`(聚搜)/`sel`(组合搜) |
| `_search_pages` | `DEFAULT_PAGES`(=10) | 并发页码，对三种模式全局生效 |
| `_sel_sites` | `[]` | 自选站点 type_id（保持选择顺序） |
| `_site_classes`/`_class_names` | `[]`/`{}` | 站点清单与中文名（homeContent 填充） |
模块级常量：`PAGE_MARKS='①②③④⑤⑥⑦⑧⑨⑩'`、`PAGE_OPTIONS=[1,3,5,8,10]`、`DEFAULT_PAGES=10`（推荐模块级，防实例重建丢失）。
## 2. 交互四件套
1. **search_menu 伪分类**：homeContent 里注册一个 `folder` 伪分类（编码进分类列表）。
2. **folder 卡**：功能卡打 `vod_tag="folder"`，点击会再次进入 `categoryContent(cid)`。
3. **编码 vod_id**：用 cid 编码动作（`sel_menu`/`sel_xvweb`/`pg_3`/`all_clear`），在 `categoryContent` 按 cid 分支，无需额外参数通道。
4. **状态变量 + 确认卡**：点击动作改状态变量，返回一张确认卡（vod_name 即结果回显，如 `已选 [小薇]`），按返回后生效。
5. **分支顺序铁律**：精确匹配（`==`）全部先于前缀匹配（`startswith`）。`pg_menu`/`pg_clear`/`all_clear` 必须先于 `cid.startswith('pg_')`，`sel_go`/`sel_all`/`sel_clear`/`sel_menu` 必须先于 `cid.startswith('sel_')`，否则前缀分支会吞掉精确卡。
## 3. 副标题「站点来源 + 页码」标记
```python
PAGE_MARKS = '①②③④⑤⑥⑦⑧⑨⑩'
mark = PAGE_MARKS[page_num - 1] if 0 < page_num <= len(PAGE_MARKS) else str(page_num)
remark = (v.get('vod_remarks') or '').strip()
v['vod_remarks'] = f"{site_name}｜{remark}｜{mark}" if remark else f"{site_name}｜{mark}"
```
页码标记取当前请求页（不负责排序，结果仍按并发完成顺序、不去重）；档位最大 10 正好 ①~⑩ 不降级。
## 4. 多选组合搜索（任意 N 站）
一级 `sel_menu` → 二级：[全选站点 / 移除全选站点 / 开始组合搜索] + N 个站点开关。
- `sel_{tid}` toggle：在 `_sel_sites` 则移除、否则追加；选中显示 `✓ 已选`。
- `sel_all`：全选站点 + 直接置 `_search_mode="agg"`（全选即聚搜）。
- `sel_clear`：清空 `_sel_sites` + 回 `single` + 回默认站源。
- `sel_go`：显式确认卡，幂等置 `sel`；空选区提示「请先选择站点」且不启用。
- searchContent 分流：`agg`→`_agg_search`；`sel`→`_sel_search`；否则单搜。
## 5. 并发页码全局化
- `PAGE_OPTIONS=[1,3,5,8,10]`，`DEFAULT_PAGES=10`；页码二级入口 `pg_menu`：首位「清空页码选择」+ 档位卡；当前档显示 `✓ 当前`。
- `pg_{n}`：`_search_pages=n`，返回确认卡。
- 全局生效：单搜/聚搜/组合搜三个函数的 `total_pages` 全部读 `_search_pages`（模块级，见 tvbox_runtime.md），一处设置三处生效；模式与页码选择顺序无关。
## 6. 三个清空按钮语义
| 按钮 | 动作 | 结果 |
|---|---|---|
| 清空站点选择（=移除全选站点） | `_sel_sites=[]`、模式回 `single`、站源回默认 | 回归默认搜索站源 |
| 清空页码选择 | `_search_pages=DEFAULT_PAGES` | 回归默认 10 页并发 |
| 全部清空 | 站点+页码+模式全重置 | 回归默认「仓库 + 10 页」 |
清空站点 ≠ 只清列表，必须同时把模式拨回默认单搜，否则残留 `sel`/`agg` 会造成「清了但搜的还是上一批站」的错觉。
## 7. 经典 Bug：勾选站点不生效（必读）
现象：先选页码再进组合搜索勾选站点，返回直接搜索 → 仍是默认仓库资源，唯独页码生效。
根因：① 分流只看 `_search_mode`；② toggle 分支只增删 `_sel_sites` 列表、从不设置 `_search_mode`，模式切换依赖用户额外点一次「开始组合搜索」。
修复（勾选即生效）：
```python
if cid.startswith('sel_'):
    tid = cid[len('sel_'):]
    if tid in self._sel_sites:
        self._sel_sites.remove(tid)
        if self._search_mode == 'agg':
            self._search_mode = 'sel'      # 从全选聚搜中减站 → 转按当前所选集合组合搜
        if not self._sel_sites:            # 全部取消：回归默认仓库单搜
            self._search_mode = 'single'; self._search_tid = 'cangku'; self._search_name = '仓库'
    else:
        self._sel_sites.append(tid)
        self._search_mode = 'sel'          # ★ 勾选即启用组合搜索，无需再点开始
```
| 场景 | 行为 |
|---|---|
| 勾选站点 | 隐式置 `sel`，直接返回搜索即按所选站 × 当前页数 |
| 取消到空集 | 自动回归默认 `single` + 默认站源 |
| 全选聚搜后手动减站 | 自动转 `sel`（否则取消对 agg 无效） |
## 8. 苹果CMS 搜索并发实现（花都参考）
```python
max_pages = _SEARCH_PAGES
with ThreadPoolExecutor(max_workers=min(max_pages, 8)) as ex:
    futures = [ex.submit(fetch_page, p) for p in range(1, max_pages + 1)]
    for f in as_completed(futures, timeout=20):
        all_videos.extend(f.result() or [])
```
- 单页丢弃三条件：空 html / 含 `站点维护` / `len(html) < 500`。
- 解析后再过滤 `vod_id` 为空。
- 结果按完成顺序 append：不去重、不保序、无延迟。
- 花都 `page_cfg|N` 编码：搜索列表页把 `page_cfg|N` 解析到 `ext['page_cfg']`，穿透到 `searchContentPage` 直接生效指定页数。
## 9. 易错点
1. 实例状态丢失 → 提为类属性/模块级。
2. 分支顺序 → 精确 `==` 全在前、`startswith` 在后，各自防 `int()` 解析失败。
3. 清站点必须拨回默认模式；聚搜减站必须转 `sel`。
4. 页码标记防越界：`0 < n <= len(PAGE_MARKS)`。
5. 空选区防护：`sel_go` 空选区不启用；`sel` 模式空选区搜索返回空列表不报错。
6. 站名回显来自 `_search_name`（init 给中文），别让 `or site_id` 兜底成英文 tid。
## 10. 验证方法论（mock base.spider）
构造 4 站 `_site_classes/_class_names/folder_cates`，用 `_req_log` 断言请求集合与次数（N 站 × M 页 = N×M）。断言清单：默认状态值；菜单卡顺序（一级 3 卡、二级前置卡）；勾选即生效（先页码再勾选→直搜）；三清空各自/全部回归默认；页码对三种模式生效；副标题格式；空选区安全。