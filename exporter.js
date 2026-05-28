/**
 * Gaijin Marketplace Vehicles Exporter (Gaijin 市场全部载具数据导出脚本 - v2版)
 * 
 * 使用方法：
 * 1. 在 Chrome 中打开 https://trade.gaijin.net/?category=vehicles 并登录您的账户。
 *    （您也可以在其他已筛选的市场页面运行此脚本）
 * 2. 按 F12 打开开发者工具，切换到 "Console" (控制台) 选项卡。
 * 3. 将此脚本复制并粘贴到控制台中，然后按 Enter 键运行。
 * 4. 脚本会扫描各市场分页，并在抓取各详情页数据后自动下载 JSON 数据文件。
 */

(async () => {
    // ---------------- 配置参数 ----------------
    const MAX_PAGES = 0;      // 最大抓取页数（0 表示无限制，即抓取所有页。调试或测试时可设为如 2）
    const CONCURRENCY = 4;     // 并发抓取数（建议保持在 3-5，防止被 Gaijin 暂时风控）
    const DELAY_MS = 500;      // 抓取完每个物品后的基础防风控延迟（毫秒）
    // ------------------------------------------

    const LOG_STYLE_HEADER = 'color: #e0a96d; font-weight: bold; background: #1a1a1e; padding: 6px 12px; border-radius: 4px; border: 1px solid #e0a96d; font-size: 13px;';
    const LOG_STYLE_INFO = 'color: #a8aab2;';
    const LOG_STYLE_SUCCESS = 'color: #7ee787; font-weight: bold;';
    const LOG_STYLE_WARN = 'color: #ff7b72; font-weight: bold;';
    const LOG_STYLE_EMPHASIS = 'color: #e0a96d; font-weight: bold;';

    console.log("%c[Gaijin Market Analyst v2] 全市场载具数据导出脚本启动", LOG_STYLE_HEADER);

    // URL 校验与提示
    if (!window.location.search.includes('category=vehicles')) {
        console.log("%c[提示] 您当前未处于 vehicles (载具) 分类页，脚本将抓取当前分类下的所有商品。", LOG_STYLE_WARN);
    }
    console.log("%c正在自动扫描市场列表，请保持该页面为当前活动标签页，不要关闭...", LOG_STYLE_INFO);

    // 辅助睡眠函数
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // 自动平滑滚动以触发图片和 DOM 懒加载
    async function triggerLazyLoad() {
        const distance = 200; // 每次滑动的距离(px)
        const delay = 35;     // 每次滑动的间隔(ms)
        while (window.scrollY + window.innerHeight < document.documentElement.scrollHeight) {
            window.scrollBy(0, distance);
            await sleep(delay);
        }
        // 平滑滚回顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
        await sleep(500); // 等待滚动回弹和渲染
    }

    // 动态获取真正的 trade_server 地址
    function getTradeServer() {
        try {
            if (window.SettingsInjections && typeof window.SettingsInjections.getUsedCircuit === 'function') {
                const circuit = window.SettingsInjections.getUsedCircuit();
                if (circuit && circuit.trade_server) {
                    return circuit.trade_server;
                }
            }
        } catch (e) {
            console.log("%c[警告] 无法通过 SettingsInjections 动态获取 trade_server, 将使用默认值", LOG_STYLE_WARN);
        }
        return "https://market-proxy.gaijin.net/web";
    }

    // 递归获取元素中所有叶子文本节点（跳过 button、script、style 等）并清洗零宽字符
    function getLeafTexts(el) {
        const texts = [];

        function traverse(node) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const tagName = node.tagName.toLowerCase();
                if (tagName === 'button' || tagName === 'script' || tagName === 'style') {
                    return;
                }
            }

            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                const cleanText = text.replace(/[\u200b\u200c\u200d\ufeff]/g, '').trim();
                if (cleanText) {
                    texts.push(cleanText);
                }
            } else {
                for (let child of node.childNodes) {
                    traverse(child);
                }
            }
        }

        traverse(el);
        return texts;
    }

    // 寻找下一页按钮
    function findNextPageButton() {
        const nextSelectors = [
            'button.next', 'a.next',
            '.pagination-next', '.pagination .next',
            '[class*="pagination"] [class*="next"]',
            '.pager-next', 'a[rel="next"]'
        ];
        for (const selector of nextSelectors) {
            const btn = document.querySelector(selector);
            if (btn && !btn.classList.contains('disabled') && btn.getAttribute('aria-disabled') !== 'true') {
                return btn;
            }
        }

        // 基于文本内容的兜底查找
        const allButtons = document.querySelectorAll('button, a, span');
        for (const el of allButtons) {
            const text = el.innerText.trim();
            if ((text === '>' || text.toLowerCase().includes('next') || text.includes('下一页')) &&
                el.offsetWidth > 0 && el.offsetHeight > 0) {
                if (!el.classList.contains('disabled') && !el.hasAttribute('disabled')) {
                    return el;
                }
            }
        }
        return null;
    }

    // 抓取当前页面卡片数据的函数
    function scrapeCurrentPage(itemsMap) {
        // 在市场主页上，匹配带市场详情的 a.lot 节点
        const itemCards = document.querySelectorAll('a.lot, a[href*="/market/"], .lot');
        let pageItemsCount = 0;

        itemCards.forEach(el => {
            let href = el.getAttribute('href');
            if (!href && el.tagName !== 'A') {
                const anchor = el.querySelector('a');
                if (anchor) href = anchor.getAttribute('href');
            }

            if (!href || !href.includes('/market/')) return;

            // 清洗详情页 URL，剔除无用 query 参数
            const cleanPath = href.split('?')[0];

            // 校验是否为合规的物品详情页链接（格式类似: /market/1067/id50257_object_292_ussr）
            const parts = cleanPath.split('/').filter(Boolean);
            if (parts.length < 3 || parts[0] !== 'market') return;

            const fullUrl = new URL(cleanPath, window.location.origin).toString();

            // 深度优先提取所有叶子文本节点
            const texts = getLeafTexts(el);
            const cleanParts = texts.filter(t => t !== "War Thunder");
            if (cleanParts.length === 0) return;

            // 在全市场载具中，名字通常是文本中的首个高亮项，最低挂单售价通常是最后一个文本值
            // 数量默认设为 1，代表在全市场分析中作为一个独特载具样本
            const quantity = 1;
            const itemName = cleanParts[0];
            if (!itemName) return;

            let sellPrice = null;
            if (cleanParts.length > 1) {
                const lastPart = cleanParts[cleanParts.length - 1];
                const priceVal = parseFloat(lastPart.replace(/[^\d.]/g, ''));
                if (!isNaN(priceVal)) {
                    sellPrice = priceVal;
                }
            }

            // 提取图片链接
            const imgEl = el.querySelector('img');
            const imageUrl = imgEl ? imgEl.src : '';

            // 更新或追加到 Map
            if (!itemsMap.has(itemName)) {
                itemsMap.set(itemName, {
                    name: itemName,
                    url: fullUrl,
                    imageUrl: imageUrl,
                    quantity: quantity,
                    sellPrice: sellPrice,
                    sellOrders: 0
                });
                pageItemsCount++;
            }
        });

        return pageItemsCount;
    }

    // 1. 开始多页扫描
    const itemsMap = new Map();
    let pageNum = 1;

    while (true) {
        console.log(`%c正在扫描第 ${pageNum} 页的载具卡片...`, LOG_STYLE_INFO);
        await triggerLazyLoad();
        const count = scrapeCurrentPage(itemsMap);
        console.log(`%c第 ${pageNum} 页扫描完毕，新增识别了 ${count} 种独特物品。累计独特物品总数: ${itemsMap.size}`, LOG_STYLE_INFO);

        // 判断是否达到最大抓取页数限制
        if (MAX_PAGES > 0 && pageNum >= MAX_PAGES) {
            console.log(`%c已达到设定的最大翻页数限制 (MAX_PAGES = ${MAX_PAGES})，结束列表扫描。`, LOG_STYLE_WARN);
            break;
        }

        const nextBtn = findNextPageButton();
        if (!nextBtn) {
            console.log("%c未发现可点击的下一页按钮，结束列表扫描。", LOG_STYLE_SUCCESS);
            break;
        }

        // 获取当前页第一个匹配的卡片文本，用于比对翻页后是否更新
        const firstCard = document.querySelector('a.lot, a[href*="/market/"]');
        const firstCardTextBefore = firstCard ? firstCard.innerText : '';

        console.log("%c检测到下一页，正在模拟点击翻页...", LOG_STYLE_INFO);
        nextBtn.click();

        // 轮询等待新页面加载（最多 5 秒）
        let loaded = false;
        for (let attempt = 0; attempt < 25; attempt++) {
            await sleep(200);
            const currentFirstCard = document.querySelector('a.lot, a[href*="/market/"]');
            const firstCardTextAfter = currentFirstCard ? currentFirstCard.innerText : '';
            if (firstCardTextAfter && firstCardTextAfter !== firstCardTextBefore) {
                loaded = true;
                break;
            }
        }

        if (!loaded) {
            await sleep(1000); // 兜底等待
            const currentFirstCard = document.querySelector('a.lot, a[href*="/market/"]');
            const firstCardTextAfter = currentFirstCard ? currentFirstCard.innerText : '';
            if (firstCardTextAfter === firstCardTextBefore) {
                console.log("%c点击翻页后页面未见刷新或加载超时，停止翻页扫描。", LOG_STYLE_WARN);
                break;
            }
        }

        pageNum++;
        await sleep(500); // 翻页缓冲
    }

    const itemsList = Array.from(itemsMap.values());

    if (itemsList.length === 0) {
        console.log("%c[错误] 未能在当前页面中找到任何有效的载具交易卡片。请确认您已打开 https://trade.gaijin.net/?category=vehicles 页面。", LOG_STYLE_WARN);
        return;
    }

    console.log(`%c[成功] 列表扫描完成！共识别到 ${itemsList.length} 种独特载具。`, LOG_STYLE_SUCCESS);

    // 估算并报告需要抓取的总时长
    const estSec = ((itemsList.length * (DELAY_MS + 350)) / CONCURRENCY / 1000).toFixed(0);
    const estMin = (estSec / 60).toFixed(1);
    console.log(`%c[优化版] 启动并发管道机制，并发数: ${CONCURRENCY}，基础延迟: ${DELAY_MS}ms。\n预估总计需要约 ${estSec} 秒 (${estMin} 分钟)，请保持此页面打开状态...`, LOG_STYLE_INFO);

    // 2. 提取 auth token，并依次拉取详情数据，补充买一价、求购单数和走势数据
    let token = null;
    let rawTokenPair = null;
    try {
        const tokenPairStr = window.localStorage.getItem('MarketApp,auth,tokenPair');
        if (tokenPairStr) {
            rawTokenPair = JSON.parse(tokenPairStr);
            token = rawTokenPair.token || rawTokenPair.gseaToken;
        }
    } catch (e) {
        console.log("%c[警告] 无法从 localStorage 中解析 tokenPair", LOG_STYLE_WARN);
    }
    if (token) {
        console.log(`%c[成功] 成功提取到登录 Token (前10位: ${token.substring(0, 10)}...)`, LOG_STYLE_SUCCESS);
    } else {
        console.log("%c[提示] 未获取到登录 Token。由于您是公开查询，API 获取某些历史均价曲线或挂单可能会受限，我们将尽可能抓取可用数据。\n自查方法：可在 Console 中执行 localStorage.getItem('MarketApp,auth,tokenPair') 检查输出。", LOG_STYLE_WARN);
    }

    const marketData = [];
    let completed = 0;
    const totalCount = itemsList.length;

    // 自研精炼极速通道并发池
    async function worker(queue) {
        while (queue.length > 0) {
            const item = queue.shift();
            if (!item) continue;
            
            try {
                const urlObj = new URL(item.url);
                const pathParts = urlObj.pathname.split('/').filter(Boolean); // ["market", "1067", "id50257_object_292_ussr"]
                const appid = pathParts[1] || "1067";
                const market_name = decodeURIComponent(pathParts[pathParts.length - 1]);

                let buyPrice = null;
                let buyOrders = 0;
                let priceHistory = [];

                // 1. 调用 cln_books_brief 参数
                const paramsBrief = new URLSearchParams();
                paramsBrief.append("appid", appid);
                paramsBrief.append("market_name", market_name);
                if (token) {
                    paramsBrief.append("token", token);
                }
                paramsBrief.append("action", "cln_books_brief");

                // 2. 调用 cln_get_pair_stat 参数
                const paramsStat = new URLSearchParams();
                paramsStat.append("appid", appid);
                paramsStat.append("market_name", market_name);
                paramsStat.append("currencyid", "gjn");
                if (token) {
                    paramsStat.append("token", token);
                }
                paramsStat.append("action", "cln_get_pair_stat");

                // 核心提升：两个独立网络请求并行发送 (Promise.all)
                const fetchBrief = fetch(getTradeServer(), {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: paramsBrief.toString()
                }).then(r => r.ok ? r.json() : null).catch(() => null);

                const fetchStat = fetch(getTradeServer(), {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: paramsStat.toString()
                }).then(r => r.ok ? r.json() : null).catch(() => null);

                const [dataBrief, dataStat] = await Promise.all([fetchBrief, fetchStat]);

                // 读取简报数据
                if (dataBrief && (dataBrief.success || dataBrief.result || dataBrief.response)) {
                    const result = dataBrief.result || dataBrief.response || dataBrief;

                    if (result.BUY && result.BUY.length > 0) {
                        buyPrice = parseFloat(result.BUY[0][0]) / 10000;
                    } else if (result.ordersBuy && result.ordersBuy.length > 0) {
                        buyPrice = parseFloat(result.ordersBuy[0].price);
                    }

                    if (result.depth && result.depth.BUY !== undefined) {
                        buyOrders = parseInt(result.depth.BUY, 10);
                    } else if (result.totalBuyDepth !== undefined) {
                        buyOrders = parseInt(result.totalBuyDepth, 10);
                    } else if (result.BUY) {
                        buyOrders = result.BUY.length;
                    }

                    // 权威覆盖在售价与在售数量
                    if (result.SELL && result.SELL.length > 0) {
                        item.sellPrice = parseFloat(result.SELL[0][0]) / 10000;
                    }
                    if (result.depth && result.depth.SELL !== undefined) {
                        item.sellOrders = parseInt(result.depth.SELL, 10);
                    } else if (result.SELL) {
                        item.sellOrders = result.SELL.length;
                    }
                }

                // 读取历史走势
                if (dataStat && (dataStat.success || dataStat.result || dataStat.response)) {
                    const result = dataStat.result || dataStat.response || dataStat;
                    const rawHistory = result["1d"] || [];
                    priceHistory = rawHistory.map(pt => {
                        return [pt[0] * 1000, parseFloat(pt[1]) / 10000];
                    });
                }

                marketData.push({
                    ...item,
                    buyPrice: buyPrice,
                    buyOrders: buyOrders,
                    history: priceHistory,
                    scrapedAt: new Date().toISOString()
                });

            } catch (err) {
                console.log(`%c[警告] "${item.name}" 数据部分抓取失败: ${err.message}`, LOG_STYLE_WARN);
                marketData.push({
                    ...item,
                    buyPrice: null,
                    buyOrders: 0,
                    history: [],
                    error: err.message,
                    scrapedAt: new Date().toISOString()
                });
            }

            completed++;
            const progress = ((completed / totalCount) * 100).toFixed(0);
            console.log(`%c[${completed}/${totalCount} - ${progress}%] %c${item.name} %c抓取补充完毕`, LOG_STYLE_INFO, LOG_STYLE_EMPHASIS, LOG_STYLE_SUCCESS);

            // 配合通道的防风控延迟
            const delay = DELAY_MS + Math.random() * 200;
            await sleep(delay);
        }
    }

    // 启动多 Worker 管道并发提取
    const queue = [...itemsList];
    const workers = [];
    for (let i = 0; i < CONCURRENCY; i++) {
        workers.push(worker(queue));
    }
    await Promise.all(workers);

    console.log("%c所有市场载具数据抓取完毕！正在生成并下载数据文件...", LOG_STYLE_SUCCESS);

    // 3. 导出 JSON 并下载
    const blob = new Blob([JSON.stringify(marketData, null, 4)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const dateStr = new Date().toISOString().split('T')[0];
    const filename = `gaijin_market_${dateStr}.json`;

    const downloadAnchor = document.createElement('a');
    downloadAnchor.href = url;
    downloadAnchor.download = filename;
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    document.body.removeChild(downloadAnchor);
    URL.revokeObjectURL(url);

    console.log(`%c[完成] 市场大盘数据文件 "${filename}" 已成功下载并保存至本地。`, LOG_STYLE_SUCCESS);
    console.log("%c请将其复制到您的本地 v2 脚本工作区，并运行 'python analyze.py' 生成最新的大盘分析报告！", LOG_STYLE_EMPHASIS);
})();
