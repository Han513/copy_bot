from __future__ import annotations

from typing import Any, Optional


TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh-TW": {
        "menu_prompt": "請選擇功能：",
        "btn_orders": "當前委託",
        "btn_positions": "當前倉位",
        "btn_balance": "可用餘額",
        "btn_language": "切換語言",
        "choose_language": "請選擇語言：",
        "lang_switched": "已切換語言。",
        "no_orders": "目前沒有委託。",
        "no_positions": "目前沒有倉位。",
        "balance": "可用餘額：<code>{balance}</code> USDT",

        # Copy / follow order flow
        "flow_balance_line": "\n当前余额：<code>{balance}</code> USDT",
        "flow_amount_prompt": (
            "請輸入保證金金額：\n"
            "例如：1000\n"
            "‼️ 按成本下單，輸入總投入金額，調整槓桿不影響成本。\n\n"
            "請使用「回覆框」輸入純數字。\n"
            "如需取消請輸入 /cancel。{bal_line}"
        ),
        "flow_amount_reply_mismatch": "請使用回覆框回覆我上一條「請輸入保證金金額」的訊息，以避免輸入錯亂。",
        "flow_amount_invalid": "金額格式不正確，請輸入純數字（例如 1000 或 12.5）。",
        "flow_amount_force_reply_placeholder": "例如：1000",

        "flow_leverage_select_prompt": "請選擇槓桿倍數或直接輸入數字（1 ~ {max_lev}）。\n例如：100\n\n如需取消請輸入 /cancel。",
        "flow_leverage_quick_select": "或點擊下方快捷按鈕：",
        "flow_leverage_custom_prompt": (
            "請您輸入想要跟單的槓桿數：1 ~ {max_lev}\n"
            "例如：50\n"
            "‼️ 選擇過高槓桿將提高強平風險，請評估自身風險承受能力。\n\n"
            "請使用「回覆框」回覆這則訊息。\n"
            "如需取消請輸入 /cancel。"
        ),
        "flow_leverage_reply_mismatch": "請使用回覆框回覆我這則訊息，輸入槓桿數（1 ~ {max_lev}）。\n例如：50",
        "flow_leverage_invalid": "槓桿格式不正確，請輸入 1 ~ {max_lev} 的整數。\n例如：50",
        "flow_leverage_placeholder": "例如：50",
        "flow_leverage_waiting_hint": "請點擊下方快捷槓桿按鈕，或點擊「自訂槓桿」後用回覆框輸入。",

        "flow_cancelled": "下单已取消。",
        "flow_button_expired": "該按鈕已過期，請重新發起跟單需求。",
        "flow_use_reply_amount_alert": "請用回覆框輸入保證金金額",
        "flow_private_only": "請在私訊操作",

        # Flow buttons
        "flow_btn_cancel": "取消下单",
        "flow_btn_edit_amount": "修改金额",
        "flow_btn_edit_leverage": "修改杠杆",
        "flow_btn_submit": "确认下单",
        "flow_btn_custom_leverage": "自訂槓桿",

        # Binding
        "bind_required": "您尚未完成 BYDFi 驗證，請先完成綁定後才能進行跟單/下單。",
        "bind_alert": "⚠️ BYDFi 驗證錯誤！\n\n💡 提示：請登入 BYDFi 平台，綁定您的 Telegram ID，以此繼續跟單！",
        "bind_jump_btn": "跳轉 BYDFi",
        "bind_verify_btn": "BYDFi 驗證",
        "bind_refresh_btn": "BYDFi 驗證",
        "bind_refresh_still_unbound": "尚未綁定成功，請先回到平台完成驗證後再點擊刷新。",
        "bind_refresh_bound_ok": "已綁定成功，正在進入跟單流程…",
        "entry_bound_prompt": "已驗證完成，點擊下方按鈕開始跟單：",
        "entry_unbound_prompt": "請先完成 BYDFi 驗證後再進行跟單：",
        "entry_one_click_btn": "一鍵跟單",

        # Exchange info validation
        "exinfo_unavailable": "暫時無法取得交易對限制資訊，請稍後再試。",
        "lev_too_high": "槓桿超過該交易對上限（最大 {max_lev}x），請重新輸入。",
        "qty_out_of_range": "下單數量超出限制（允許範圍：{min_qty} ~ {max_qty}），請調整金額或槓桿。",
        "lev_set_failed": "槓桿設定失敗，請稍後再試。",
        "notional_too_high": "本次名義價值超過限制（最大 {max_notional}），請降低槓桿或金額。",

        # API errors (platform)
        "api_err_generic": "接口錯誤",
        "api_err_unknown": "接口錯誤",
        "api_err_401": "未授權",
        "api_err_500": "系統內部錯誤",
        "api_err_501": "系統繁忙",
        "api_err_506": "未知的請求來源",
        "api_err_510": "請求過於頻繁",
        "api_err_511": "接口禁止訪問",
        "api_err_513": "請求時間無效",
        "api_err_514": "重複請求",
        "api_err_515": "無權限",
        "api_err_600": "參數錯誤",
        "api_err_1002": "交易對不支持",
        "api_err_1003": "幣種不支持",
        "api_err_1005": "帳戶餘額不足",
        "api_err_2001": "暫停交易",
        "api_err_2021": "行情錯誤",
        "api_err_2022": "行情過時",
        "api_err_2023": "禁止交易",
        "api_err_100012": "保證金不夠",
        "api_err_100014": "訂單不存在",
        "api_err_100019": "無資產",
        "api_err_100051": "杠桿超出上限",
        "api_err_200008": "合約不存在",
        "api_err_200009": "合約暫不支持該幣種",
        "api_err_200014": "撤單失敗：用戶不匹配",
        "api_err_200015": "用戶資產不足",

        # Order errors
        "order_failed": "❌ 下单失败",
        "reason_line": "原因: {reason}",
        "unknown_error": "未知错误",
        "order_delegating": "🚀 委託處理中…",
        "order_delegated_ok": "✅ 委託成功！\n订单ID：<code>{order_id}</code>\n持倉價值：<code>{position_value}</code> USDT\n状态：<b>委託成功</b>",

        # Open orders
        "orders_loading": "正在查詢中…",
        "orders_title": "📌 当前委托",
        "orders_empty": "目前沒有委託。",
        "orders_page": "第 {page}/{pages} 頁（共 {total} 筆）",
        "orders_cancel_hint": "點選下方訂單ID可撤單：",
        "orders_refresh": "刷新",
        "orders_prev": "上一頁",
        "orders_next": "下一頁",
        "orders_cancel_all_btn": "取消全部",
        "orders_cancel_all_confirm_btn": "確認取消全部",
        "orders_cancel_all_back_btn": "返回",
        "orders_cancel_all_alert": "⚠️ 將取消所有當前委託。\n\n如確認，請再點一次「確認取消全部」。",
        "orders_cancel_all_done": "已取消全部委託（共 {count} 筆）",
        "orders_cancel_all_partial": "已取消部分委託（{ok}/{total} 筆），請點擊「刷新」確認。",
        "orders_cancel_all_none": "目前沒有可取消的委託。",
        "orders_cancel_all_fail": "取消全部失敗：{reason}",
        "orders_snapshot_expired": "列表已更新（超過 {ttl} 秒），請先點擊「刷新」再撤單。",
        "orders_order_gone": "該委託已不存在/已成交，請先點擊「刷新」更新列表。",
        "orders_cancel_ok": "撤單成功",
        "orders_cancel_fail": "撤單失敗：{reason}",
        "orders_item": (
            "💡 <b>订单ID</b>：<code>{order_id}</code>\n"
            "交易对：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "杠杆：<code>{leverage}</code>x\n"
            "委托价格：<code>{price}</code>\n"
            "保证金：<code>{margin}</code> USDT\n"
            "时间：<code>{create_time}</code>"
        ),

        # Positions
        "positions_loading": "正在查詢中…",
        "positions_title": "📌 当前持仓",
        "positions_empty": "目前沒有持倉。",
        "positions_page": "第 {page}/{pages} 頁（共 {total} 筆）",
        "positions_refresh": "刷新",
        "positions_prev": "上一頁",
        "positions_next": "下一頁",
        "positions_item": (
            "💡 <b>交易对</b>：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "持仓价值：<code>{holding_value}</code> {settle}\n"
            "开仓均价：<code>{avg_price}</code>\n"
            "标记价格：<code>{mark_price}</code>\n"
            "强平价格：<code>{liq_price}</code>\n"
            "保证金：<code>{margin}</code> {settle}\n"
            "未实现盈亏：<code>{pnl}</code> {settle}（{pnl_pct}%）{tp_sl_line}"
        ),
        "tp_sl_ratio_full": "全平",
        "tp_sl_ratio_partial": "{pct}%",
        "positions_tp_sl_line": "\n止盈：<code>{tp}</code>  止损：<code>{sl}</code>",
        "positions_close_btn": "平倉 {symbol}",
        "positions_close_all_btn": "一鍵平倉",
        "positions_close_all_alert": "⚠️ 將平掉所有持倉。\n\n如確認，請再點一次「確認一鍵平倉」。",
        "positions_close_all_confirm_btn": "確認一鍵平倉",
        "positions_close_all_back_btn": "返回",
        "positions_close_hint": "點選下方平倉按鈕可平掉該持倉：",
        "positions_close_ok": "平倉成功",
        "positions_close_fail": "平倉失敗：{reason}",
        "positions_close_all_done": "已全部平倉（共 {count} 筆）",
        "positions_close_all_partial": "已平倉部分（{ok}/{total} 筆），請點擊「刷新」確認。",
        "positions_close_all_none": "目前沒有可平倉的持倉。",
        "positions_close_all_fail": "一鍵平倉失敗：{reason}",
    },
    "zh-CN": {
        "menu_prompt": "请选择功能：",
        "btn_orders": "当前委托",
        "btn_positions": "当前仓位",
        "btn_balance": "可用余额",
        "btn_language": "切换语言",
        "choose_language": "请选择语言：",
        "lang_switched": "语言已切换。",
        "no_orders": "当前没有委托。",
        "no_positions": "当前没有仓位。",
        "balance": "可用余额：<code>{balance}</code> USDT",

        # Copy / follow order flow (placeholders; you can refine wording later)
        "flow_balance_line": "\n当前余额：<code>{balance}</code> USDT",
        "flow_amount_prompt": (
            "请输入保证金金额：\n"
            "例如：1000\n"
            "‼️ 按成本下单，输入总投入金额，调整杠杆不影响成本。\n\n"
            "请使用「回复框」输入纯数字。\n"
            "如需取消请输入 /cancel。{bal_line}"
        ),
        "flow_amount_reply_mismatch": "请使用回复框回复我上一条「请输入保证金金额」的消息，以避免输入错乱。",
        "flow_amount_invalid": "金额格式不正确，请输入纯数字（例如 1000 或 12.5）。",
        "flow_amount_force_reply_placeholder": "例如：1000",

        "flow_leverage_select_prompt": "请选择杠杆倍数或直接输入数字（1 ~ {max_lev}）。\n例如：100\n\n如需取消请输入 /cancel。",
        "flow_leverage_quick_select": "或点击下方快捷按钮：",
        "flow_leverage_custom_prompt": (
            "请输入想要跟单的杠杆数：1 ~ {max_lev}\n"
            "例如：50\n"
            "‼️ 选择过高杠杆将提高强平风险，请评估自身风险承受能力。\n\n"
            "请使用「回复框」回复这条消息。\n"
            "如需取消请输入 /cancel。"
        ),
        "flow_leverage_reply_mismatch": "请使用回复框回复我这条消息，输入杠杆数（1 ~ {max_lev}）。\n例如：50",
        "flow_leverage_invalid": "杠杆格式不正确，请输入 1 ~ {max_lev} 的整数。\n例如：50",
        "flow_leverage_placeholder": "例如：50",
        "flow_leverage_waiting_hint": "请点击下方快捷杠杆按钮，或点击「自定义杠杆」后用回复框输入。",

        "flow_cancelled": "下单已取消。",
        "flow_button_expired": "该按钮已过期，请重新发起跟单需求。",
        "flow_use_reply_amount_alert": "请用回复框输入保证金金额",
        "flow_private_only": "请在私讯操作",

        "flow_btn_cancel": "取消下单",
        "flow_btn_edit_amount": "修改金额",
        "flow_btn_edit_leverage": "修改杠杆",
        "flow_btn_submit": "确认下单",
        "flow_btn_custom_leverage": "自定义杠杆",

        # Binding
        "bind_required": "您尚未完成 BYDFi 验证，请先完成绑定后才能进行跟单/下单。",
        "bind_alert": "⚠️ BYDFi验证错误！\n\n💡 提示：请登录BYDFi平台，绑定您的Telegram ID，以此继续跟单！",
        "bind_jump_btn": "跳转BYDFi",
        "bind_verify_btn": "BYDFi 验证",
        "bind_refresh_btn": "BYDFi验证",
        "bind_refresh_still_unbound": "仍未绑定成功，请先回到平台完成验证后再点击刷新。",
        "bind_refresh_bound_ok": "已绑定成功，正在进入跟单流程…",
        "entry_bound_prompt": "已验证完成，点击下方按钮开始跟单：",
        "entry_unbound_prompt": "请先完成 BYDFi 验证后再进行跟单：",
        "entry_one_click_btn": "一键跟单",

        # Exchange info validation
        "exinfo_unavailable": "暂时无法获取交易对限制信息，请稍后再试。",
        "lev_too_high": "杠杆超过该交易对上限（最大 {max_lev}x），请重新输入。",
        "qty_out_of_range": "下单数量超出限制（允许范围：{min_qty} ~ {max_qty}），请调整金额或杠杆。",
        "lev_set_failed": "杠杆设置失败，请稍后再试。",
        "notional_too_high": "本次名义价值超过限制（最大 {max_notional}），请降低杠杆或金额。",

        # API errors (platform)
        "api_err_generic": "接口错误",
        "api_err_unknown": "接口错误",
        "api_err_401": "未授权",
        "api_err_500": "系统内部错误",
        "api_err_501": "系统繁忙",
        "api_err_506": "未知的请求来源",
        "api_err_510": "请求过于频繁",
        "api_err_511": "接口禁止访问",
        "api_err_513": "请求时间无效",
        "api_err_514": "重复请求",
        "api_err_515": "无权限",
        "api_err_600": "参数错误",
        "api_err_1002": "交易对不支持",
        "api_err_1003": "币种不支持",
        "api_err_1005": "账户余额不足",
        "api_err_2001": "暂停交易",
        "api_err_2021": "行情错误",
        "api_err_2022": "行情过时",
        "api_err_2023": "禁止交易",
        "api_err_100012": "保证金不够",
        "api_err_100014": "订单不存在",
        "api_err_100019": "无资产",
        "api_err_100051": "杠杆超出上限",
        "api_err_200008": "合约不存在",
        "api_err_200009": "合约暂不支持该币种",
        "api_err_200014": "撤单失败：用户不匹配",
        "api_err_200015": "用户资产不足",

        # Order errors
        "order_failed": "❌ 下单失败",
        "reason_line": "原因: {reason}",
        "unknown_error": "未知错误",
        "order_delegating": "🚀 委托处理中…",
        "order_delegated_ok": "✅ 委托成功！\n订单ID：<code>{order_id}</code>\n持仓价值：<code>{position_value}</code> USDT\n状态：<b>委托成功</b>",

        # Open orders
        "orders_loading": "正在查询中…",
        "orders_title": "📌 当前委托",
        "orders_empty": "当前没有委托。",
        "orders_page": "第 {page}/{pages} 页（共 {total} 笔）",
        "orders_cancel_hint": "点击下方订单ID可撤单：",
        "orders_refresh": "刷新",
        "orders_prev": "上一页",
        "orders_next": "下一页",
        "orders_cancel_all_btn": "取消全部",
        "orders_cancel_all_confirm_btn": "确认取消全部",
        "orders_cancel_all_back_btn": "返回",
        "orders_cancel_all_alert": "⚠️ 将取消所有当前委托。\n\n如确认，请再点一次「确认取消全部」。",
        "orders_cancel_all_done": "已取消全部委托（共 {count} 笔）",
        "orders_cancel_all_partial": "已取消部分委托（{ok}/{total} 笔），请点击「刷新」确认。",
        "orders_cancel_all_none": "当前没有可取消的委托。",
        "orders_cancel_all_fail": "取消全部失败：{reason}",
        "orders_snapshot_expired": "列表已更新（超过 {ttl} 秒），请先点击「刷新」再撤单。",
        "orders_order_gone": "该委托已不存在/已成交，请先点击「刷新」更新列表。",
        "orders_cancel_ok": "撤单成功",
        "orders_cancel_fail": "撤单失败：{reason}",
        "orders_item": (
            "💡 <b>订单ID</b>：<code>{order_id}</code>\n"
            "交易对：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "杠杆：<code>{leverage}</code>x\n"
            "委托价格：<code>{price}</code>\n"
            "保证金：<code>{margin}</code> USDT\n"
            "时间：<code>{create_time}</code>"
        ),

        # Positions
        "positions_loading": "正在查询中…",
        "positions_title": "📌 当前持仓",
        "positions_empty": "当前没有持仓。",
        "positions_page": "第 {page}/{pages} 页（共 {total} 笔）",
        "positions_refresh": "刷新",
        "positions_prev": "上一页",
        "positions_next": "下一页",
        "positions_item": (
            "💡 <b>交易对</b>：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "持仓价值：<code>{holding_value}</code> {settle}\n"
            "开仓均价：<code>{avg_price}</code>\n"
            "标记价格：<code>{mark_price}</code>\n"
            "强平价格：<code>{liq_price}</code>\n"
            "保证金：<code>{margin}</code> {settle}\n"
            "未实现盈亏：<code>{pnl}</code> {settle}（{pnl_pct}%）{tp_sl_line}"
        ),
        "tp_sl_ratio_full": "全平",
        "tp_sl_ratio_partial": "{pct}%",
        "positions_tp_sl_line": "\n止盈：<code>{tp}</code>  止损：<code>{sl}</code>",
        "positions_close_btn": "平仓 {symbol}",
        "positions_close_all_btn": "一键平仓",
        "positions_close_all_alert": "⚠️ 将平掉所有持仓。\n\n如确认，请再点一次「确认一键平仓」。",
        "positions_close_all_confirm_btn": "确认一键平仓",
        "positions_close_all_back_btn": "返回",
        "positions_close_hint": "点击下方平仓按钮可平掉该持仓：",
        "positions_close_ok": "平仓成功",
        "positions_close_fail": "平仓失败：{reason}",
        "positions_close_all_done": "已全部平仓（共 {count} 笔）",
        "positions_close_all_partial": "已平仓部分（{ok}/{total} 笔），请点击「刷新」确认。",
        "positions_close_all_none": "当前没有可平仓的持仓。",
        "positions_close_all_fail": "一键平仓失败：{reason}",
    },
    "en": {
        "menu_prompt": "Choose an action:",
        "btn_orders": "Open orders",
        "btn_positions": "Positions",
        "btn_balance": "Available balance",
        "btn_language": "Language",
        "choose_language": "Choose a language:",
        "lang_switched": "Language updated.",
        "no_orders": "No open orders.",
        "no_positions": "No positions.",
        "balance": "Available balance: <code>{balance}</code> USDT",

        # Copy / follow order flow (placeholders; user will refine later)
        "flow_balance_line": "\nAvailable balance: <code>{balance}</code> USDT",
        "flow_amount_prompt": (
            "Please enter the margin amount:\n"
            "e.g. 1000\n"
            "‼️ Cost-based order: enter total invested amount; leverage changes won't change cost.\n\n"
            "Use the reply box and enter numbers only.\n"
            "To cancel, type /cancel.{bal_line}"
        ),
        "flow_amount_reply_mismatch": "Please reply to my previous margin prompt using the reply box to avoid confusion.",
        "flow_amount_invalid": "Invalid amount. Please enter numbers only (e.g. 1000 or 12.5).",
        "flow_amount_force_reply_placeholder": "e.g. 1000",

        "flow_leverage_select_prompt": "Choose leverage or type a number directly (1 ~ {max_lev}).\ne.g. 100\n\nTo cancel, type /cancel.",
        "flow_leverage_quick_select": "Or tap a quick-select button below:",
        "flow_leverage_custom_prompt": (
            "Enter leverage for copy trading: 1 ~ {max_lev}\n"
            "e.g. 50\n"
            "‼️ High leverage increases liquidation risk. Please assess your risk tolerance.\n\n"
            "Reply to this message using the reply box.\n"
            "To cancel, type /cancel."
        ),
        "flow_leverage_reply_mismatch": "Please reply to this message and enter leverage (1 ~ {max_lev}). e.g. 50",
        "flow_leverage_invalid": "Invalid leverage. Please enter an integer between 1 and {max_lev}. e.g. 50",
        "flow_leverage_placeholder": "e.g. 50",
        "flow_leverage_waiting_hint": "Tap a leverage button below, or tap “Custom leverage” to input via reply box.",

        "flow_cancelled": "Order cancelled.",
        "flow_button_expired": "This button has expired. Please initiate a new copy order request.",
        "flow_use_reply_amount_alert": "Please input margin via reply box",
        "flow_private_only": "Please use private chat",

        "flow_btn_cancel": "Cancel",
        "flow_btn_edit_amount": "Edit amount",
        "flow_btn_edit_leverage": "Edit leverage",
        "flow_btn_submit": "Confirm",
        "flow_btn_custom_leverage": "Custom leverage",

        # Binding
        "bind_required": "You haven't completed BYDFi verification. Please bind your account before copy trading / placing orders.",
        "bind_alert": "⚠️ BYDFi verification required.\n\nPlease log in to BYDFi and bind your Telegram ID before continuing.",
        "bind_jump_btn": "Go to BYDFi",
        "bind_verify_btn": "BYDFi Verify",
        "bind_refresh_btn": "I’ve verified (Refresh)",
        "bind_refresh_still_unbound": "Not bound yet. Please complete verification on the platform and tap refresh again.",
        "bind_refresh_bound_ok": "Bound successfully. Continuing…",
        "entry_bound_prompt": "Verified. Tap the button below to start copy trading:",
        "entry_unbound_prompt": "Please verify with BYDFi before continuing:",
        "entry_one_click_btn": "One-click copy",

        # Exchange info validation
        "exinfo_unavailable": "Unable to load symbol limits right now. Please try again later.",
        "lev_too_high": "Leverage exceeds symbol limit (max {max_lev}x). Please enter again.",
        "qty_out_of_range": "Order quantity out of range ({min_qty} ~ {max_qty}). Please adjust amount or leverage.",
        "lev_set_failed": "Failed to set leverage. Please try again later.",
        "notional_too_high": "Notional exceeds limit (max {max_notional}). Please reduce leverage or amount.",

        # API errors (platform)
        "api_err_generic": "API error",
        "api_err_unknown": "API error",
        "api_err_401": "Unauthorized",
        "api_err_500": "Internal error",
        "api_err_501": "System busy",
        "api_err_506": "Unknown request source",
        "api_err_510": "Too many requests",
        "api_err_511": "API access forbidden",
        "api_err_513": "Invalid request time",
        "api_err_514": "Duplicate request",
        "api_err_515": "No permission",
        "api_err_600": "Parameter error",
        "api_err_1002": "Trading pair not supported",
        "api_err_1003": "Currency not supported",
        "api_err_1005": "Insufficient balance",
        "api_err_2001": "Trading paused",
        "api_err_2021": "Market error",
        "api_err_2022": "Market data is stale",
        "api_err_2023": "Trading forbidden",
        "api_err_100012": "Insufficient margin",
        "api_err_100014": "Order not found",
        "api_err_100019": "No assets",
        "api_err_100051": "Leverage exceeds maximum allowed",
        "api_err_200008": "Contract not found",
        "api_err_200009": "Contract/currency not supported",
        "api_err_200014": "Cancel failed: user mismatch",
        "api_err_200015": "Insufficient user assets",

        # Order errors
        "order_failed": "❌ Order failed",
        "reason_line": "Reason: {reason}",
        "unknown_error": "Unknown error",
        "order_delegating": "🚀 Submitting order…",
        "order_delegated_ok": "✅ Order delegated!\nOrder ID: <code>{order_id}</code>\nPosition value: <code>{position_value}</code> USDT\nStatus: <b>Delegated</b>",

        # Open orders
        "orders_loading": "Loading open orders…",
        "orders_title": "📌 Open orders",
        "orders_empty": "No open orders.",
        "orders_page": "Page {page}/{pages} (total {total})",
        "orders_cancel_hint": "Tap an order ID below to cancel:",
        "orders_refresh": "Refresh",
        "orders_prev": "Prev",
        "orders_next": "Next",
        "orders_cancel_all_btn": "Cancel all",
        "orders_cancel_all_confirm_btn": "Confirm cancel all",
        "orders_cancel_all_back_btn": "Back",
        "orders_cancel_all_alert": "⚠️ This will cancel ALL open orders.\n\nIf you’re sure, tap “Confirm cancel all” again.",
        "orders_cancel_all_done": "All open orders cancelled ({count})",
        "orders_cancel_all_partial": "Partially cancelled ({ok}/{total}). Please tap Refresh to confirm.",
        "orders_cancel_all_none": "No open orders to cancel.",
        "orders_cancel_all_fail": "Cancel all failed: {reason}",
        "orders_snapshot_expired": "This list is outdated (>{ttl}s). Please tap Refresh before cancelling.",
        "orders_order_gone": "This order no longer exists / is already filled. Please Refresh the list.",
        "orders_cancel_ok": "Order cancelled",
        "orders_cancel_fail": "Cancel failed: {reason}",
        "orders_item": (
            "💡 <b>Order ID</b>: <code>{order_id}</code>\n"
            "Symbol: <code>{symbol}</code>\n"
            "Side: {side}\n"
            "Leverage: <code>{leverage}</code>x\n"
            "Price: <code>{price}</code>\n"
            "Margin: <code>{margin}</code> USDT\n"
            "Time: <code>{create_time}</code>"
        ),

        # Positions
        "positions_loading": "Loading positions…",
        "positions_title": "📌 Positions",
        "positions_empty": "No positions.",
        "positions_page": "Page {page}/{pages} (total {total})",
        "positions_refresh": "Refresh",
        "positions_prev": "Prev",
        "positions_next": "Next",
        "positions_item": (
            "💡 <b>Symbol</b>: <code>{symbol}</code>\n"
            "Side: {side}\n"
            "Value: <code>{holding_value}</code> {settle}\n"
            "Avg: <code>{avg_price}</code>\n"
            "Mark: <code>{mark_price}</code>\n"
            "Liq: <code>{liq_price}</code>\n"
            "Margin: <code>{margin}</code> {settle}\n"
            "uPnL: <code>{pnl}</code> {settle} ({pnl_pct}%){tp_sl_line}"
        ),
        "tp_sl_ratio_full": "Full",
        "tp_sl_ratio_partial": "{pct}%",
        "positions_tp_sl_line": "\nTP: <code>{tp}</code>  SL: <code>{sl}</code>",
        "positions_close_btn": "Close {symbol}",
        "positions_close_all_btn": "Close all",
        "positions_close_all_alert": "⚠️ This will close ALL positions.\n\nIf you're sure, tap \"Confirm close all\" again.",
        "positions_close_all_confirm_btn": "Confirm close all",
        "positions_close_all_back_btn": "Back",
        "positions_close_hint": "Tap below to close that position:",
        "positions_close_ok": "Position closed",
        "positions_close_fail": "Close failed: {reason}",
        "positions_close_all_done": "All positions closed ({count})",
        "positions_close_all_partial": "Partially closed ({ok}/{total}). Please tap Refresh to confirm.",
        "positions_close_all_none": "No positions to close.",
        "positions_close_all_fail": "Close all failed: {reason}",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    table = TRANSLATIONS.get(lang) or TRANSLATIONS["zh-TW"]
    template = table.get(key) or TRANSLATIONS["zh-TW"].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def all_button_texts() -> set[str]:
    keys = {"btn_orders", "btn_positions", "btn_balance", "btn_language"}
    out: set[str] = set()
    for lang_table in TRANSLATIONS.values():
        for k in keys:
            v = lang_table.get(k)
            if v:
                out.add(v)
    return out


def get_button_key(text: str) -> Optional[str]:
    """依按鈕文字回傳對應的 i18n key，若無則回傳 None"""
    keys = ("btn_balance", "btn_orders", "btn_positions", "btn_language")
    for key in keys:
        for lang_table in TRANSLATIONS.values():
            if lang_table.get(key) == text:
                return key
    return None

