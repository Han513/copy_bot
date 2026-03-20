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
        "flow_balance_line": "\n當前餘額：<code>{balance}</code> USDT",
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

        "flow_cancelled": "下單已取消。",
        "flow_button_expired": "該按鈕已過期，請重新發起跟單需求。",
        "flow_use_reply_amount_alert": "請用回覆框輸入保證金金額",
        "flow_private_only": "請在私訊操作",

        # Flow buttons
        "flow_btn_cancel": "取消下單",
        "flow_btn_edit_amount": "修改金額",
        "flow_btn_edit_leverage": "修改槓桿",
        "flow_btn_submit": "確認下單",
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

        # Signal card (follow-order message)
        "signal_title_default": "交易信號",
        "signal_id": "信號ID",
        "signal_trading_pair": "交易對",
        "signal_direction": "方向",
        "direction_long": "多",
        "direction_short": "空",
        "signal_entry_price": "進場價格",
        "signal_take_profit": "止盈價格",
        "signal_stop_loss": "止損價格",
        "signal_validity": "有效期",
        "signal_validity_hours": "{n}小時",
        "signal_validity_seconds": "{n}秒",
        "signal_validity_until": "截止 {dt}",

        # Confirm order (copy flow)
        "flow_confirm_prompt": "請確認訂單資訊：\n\n",
        "flow_confirm_amount": "跟單金額",
        "flow_confirm_leverage": "槓桿倍數",

        # Flow / signal errors & hints
        "init_not_ready": "系統尚未完成初始化，請稍後再試。",
        "flow_state_expired": "狀態已失效，請回到頻道重新點擊『一鍵跟單』。",
        "flow_signal_expired_ttl": "當前信號已失效（超過有效期），無法繼續操作。請回到頻道查看最新信號。",
        "flow_signal_expired_generic": "當前信號失效，無法操作。",
        "flow_fetch_signal_fail": "獲取信號詳情失敗（可能已過期或不存在）。請回到頻道查看最新信號。",
        "flow_signal_expired_deeplink": "當前信號已失效（超過有效期），無法跟單。請回到頻道查看最新信號。",
        "start_prompt": "已啟動。請到公開頻道點擊『一鍵跟單』按鈕開始。\n\n指令：/balance 查詢餘額",
        "flow_insufficient_balance": "下單失敗：餘額不足，請充值。",
        "flow_private_only_alert": "請在私訊操作",
        "flow_unsupported_lang": "不支援的語言",
        "flow_leverage_invalid_alert": "槓桿不正確",
        "flow_private_operate": "請在私訊完成操作",
        "flow_platform_not_configured": "系統未配置 PLATFORM_API_BASE_URL，無法下單。",
        "flow_channel_hint": "請點擊頻道訊息中的按鈕，並在與機器人的私訊中完成跟單流程。",
        "cmd_balance_private": "請在私訊使用此指令。",

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
        "api_err_1002": "交易對不支援",
        "api_err_1003": "幣種不支援",
        "api_err_1005": "帳戶餘額不足",
        "api_err_2001": "暫停交易",
        "api_err_2021": "行情錯誤",
        "api_err_2022": "行情過時",
        "api_err_2023": "禁止交易",
        "api_err_100012": "保證金不夠",
        "api_err_100014": "訂單不存在",
        "api_err_100019": "無資產",
        "api_err_100051": "槓桿超出上限",
        "api_err_200008": "合約不存在",
        "api_err_200009": "合約暫不支援該幣種",
        "api_err_200014": "撤單失敗：用戶不匹配",
        "api_err_200015": "用戶資產不足",

        # Order errors
        "order_failed": "❌ 下單失敗",
        "reason_line": "原因: {reason}",
        "unknown_error": "未知錯誤",
        "order_delegating": "🚀 委託處理中…",
        "order_delegated_ok": "✅ 委託成功！\n訂單ID：<code>{order_id}</code>\n持倉價值：<code>{position_value}</code> USDT\n狀態：<b>委託成功</b>",

        # Open orders
        "orders_loading": "正在查詢中…",
        "orders_title": "📌 當前委託",
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
            "💡 <b>訂單ID</b>：<code>{order_id}</code>\n"
            "交易對：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "槓桿：<code>{leverage}</code>x\n"
            "委託價格：<code>{price}</code>\n"
            "保證金：<code>{margin}</code> USDT\n"
            "時間：<code>{create_time}</code>"
        ),

        # Positions
        "positions_loading": "正在查詢中…",
        "positions_title": "📌 當前持倉",
        "positions_empty": "目前沒有持倉。",
        "positions_page": "第 {page}/{pages} 頁（共 {total} 筆）",
        "positions_refresh": "刷新",
        "positions_prev": "上一頁",
        "positions_next": "下一頁",
        "positions_item": (
            "💡 <b>交易對</b>：<code>{symbol}</code>\n"
            "方向：{side}\n"
            "持倉價值：<code>{holding_value}</code> {settle}\n"
            "開倉均價：<code>{avg_price}</code>\n"
            "標記價格：<code>{mark_price}</code>\n"
            "強平價格：<code>{liq_price}</code>\n"
            "保證金：<code>{margin}</code> {settle}\n"
            "未實現盈虧：<code>{pnl}</code> {settle}（{pnl_pct}%）{tp_sl_line}"
        ),
        "tp_sl_ratio_full": "全平",
        "tp_sl_ratio_partial": "{pct}%",
        "positions_tp_sl_line": "\n止盈：<code>{tp}</code>  止損：<code>{sl}</code>",
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

        # Signal card (follow-order message)
        "signal_title_default": "交易信号",
        "signal_id": "信号ID",
        "signal_trading_pair": "交易对",
        "signal_direction": "方向",
        "direction_long": "多",
        "direction_short": "空",
        "signal_entry_price": "进场价格",
        "signal_take_profit": "止盈价格",
        "signal_stop_loss": "止损价格",
        "signal_validity": "有效期",
        "signal_validity_hours": "{n}小时",
        "signal_validity_seconds": "{n}秒",
        "signal_validity_until": "截止 {dt}",

        # Confirm order (copy flow)
        "flow_confirm_prompt": "请确认订单信息：\n\n",
        "flow_confirm_amount": "跟单金额",
        "flow_confirm_leverage": "杠杆倍数",

        # Flow / signal errors & hints
        "init_not_ready": "系统尚未完成初始化，请稍后再试。",
        "flow_state_expired": "状态已失效，请回到频道重新点击「一键跟单」。",
        "flow_signal_expired_ttl": "当前信号已失效（超过有效期），无法继续操作。请回到频道查看最新信号。",
        "flow_signal_expired_generic": "当前信号失效，无法操作。",
        "flow_fetch_signal_fail": "获取信号详情失败（可能已过期或不存在）。请回到频道查看最新信号。",
        "flow_signal_expired_deeplink": "当前信号已失效（超过有效期），无法跟单。请回到频道查看最新信号。",
        "start_prompt": "已启动。请到公开频道点击「一键跟单」按钮开始。\n\n指令：/balance 查询余额",
        "flow_insufficient_balance": "下单失败：余额不足，请充值。",
        "flow_private_only_alert": "请在私讯操作",
        "flow_unsupported_lang": "不支持的语言",
        "flow_leverage_invalid_alert": "杠杆不正确",
        "flow_private_operate": "请在私讯完成操作",
        "flow_platform_not_configured": "系统未配置 PLATFORM_API_BASE_URL，无法下单。",
        "flow_channel_hint": "请点击频道消息中的按钮，并在与机器人的私讯中完成跟单流程。",
        "cmd_balance_private": "请在私讯使用此指令。",

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
        "menu_prompt": "Select Menu",
        "btn_orders": "Open Orders",
        "btn_positions": "Positions",
        "btn_balance": "Available Balance",
        "btn_language": "Switch Language",
        "choose_language": "Select Language",
        "lang_switched": "Language Updated",
        "no_orders": "No Open Orders",
        "no_positions": "No Open Positions",
        "balance": "Available Balance: <code>{balance}</code> USDT",

        # Copy / follow order flow (placeholders; user will refine later)
        "flow_balance_line": "\nAvailable balance: <code>{balance}</code> USDT",
        "flow_amount_prompt": (
            "Please enter margin amount:\n"
            "e.g. 1000\n"
            "‼️ Order by cost: Enter total investment. Changing leverage will not affect cost.\n\n"
            "Please enter numbers only in the reply box.\n"
            "To cancel, type /cancel.{bal_line}"
        ),
        "flow_amount_reply_mismatch": "Please reply to the \"Please enter margin amount\" message to avoid input errors.",
        "flow_amount_invalid": "Invalid format. Please enter numbers only (e.g., 1000 or 12.5).",
        "flow_amount_force_reply_placeholder": "e.g. 1000",

        "flow_leverage_select_prompt": "Select leverage or enter a number (1 ~ {max_lev}).\ne.g. 100\n\nTo cancel, type /cancel.",
        "flow_leverage_quick_select": "Or use the quick-select buttons below",
        "flow_leverage_custom_prompt": (
            "Enter the copy trading leverage: 1 ~ {max_lev}\n"
            "e.g. 50\n"
            "‼️ High leverage increases liquidation risk. Please assess your risk tolerance.\n\n"
            "Please use the 'Reply' function to respond to this message.\n"
            "To cancel, type /cancel."
        ),
        "flow_leverage_reply_mismatch": "Please reply to this message with your leverage (1 ~ {max_lev}).",
        "flow_leverage_invalid": "Invalid format. Please enter an integer between 1 and {max_lev}.",
        "flow_leverage_placeholder": "e.g., 50",
        "flow_leverage_waiting_hint": "Select a quick-leverage button below, or click Custom Leverage and reply to this message.",

        "flow_cancelled": "Order has been cancelled.",
        "flow_button_expired": "This button has expired. Please restart the copy-trading request.",
        "flow_use_reply_amount_alert": "Please reply to this message with the margin amount.",
        "flow_private_only": "Please proceed in Direct Message (DM).",

        "flow_btn_cancel": "Cancel Order",
        "flow_btn_edit_amount": "Edit Amount",
        "flow_btn_edit_leverage": "Edit Leverage",
        "flow_btn_submit": "Confirm Order",
        "flow_btn_custom_leverage": "Custom Leverage",

        # Binding
        "bind_required": "BYDFi verification incomplete. Please bind your account to start copy trading.",
        "bind_alert": "⚠️ BYDFi Verification Error!\n\nPlease log in to BYDFi and bind your Telegram ID to continue copy trading.",
        "bind_jump_btn": "Continue on BYDFi",
        "bind_verify_btn": "BYDFi Verification",
        "bind_refresh_btn": "BYDFi Verification",
        "bind_refresh_still_unbound": "Binding failed. Please complete verification on the platform, then click \"Refresh\".",
        "bind_refresh_bound_ok": "Binding successful. Entering copy trade process...",
        "entry_bound_prompt": "Verification complete. Click the button below to start copy trading:",
        "entry_unbound_prompt": "Please complete BYDFi verification before copy trading:",
        "entry_one_click_btn": "One-Click Copy",

        # Signal card (follow-order message)
        "signal_title_default": "Trading Signal",
        "signal_id": "Signal ID",
        "signal_trading_pair": "Trading Pair",
        "signal_direction": "Direction",
        "direction_long": "Long",
        "direction_short": "Short",
        "signal_entry_price": "Entry Price",
        "signal_take_profit": "Take Profit",
        "signal_stop_loss": "Stop Loss",
        "signal_validity": "Validity",
        "signal_validity_hours": "{n}h",
        "signal_validity_seconds": "{n}s",
        "signal_validity_until": "until {dt}",

        # Confirm order (copy flow)
        "flow_confirm_prompt": "Please confirm order details:\n\n",
        "flow_confirm_amount": "Copy Amount",
        "flow_confirm_leverage": "Leverage",

        # Flow / signal errors & hints
        "init_not_ready": "System is initializing. Please try again later.",
        "flow_state_expired": "Session expired. Please go back to the channel and click \"One-Click Copy\" again.",
        "flow_signal_expired_ttl": "This signal has expired. Please go back to the channel for the latest signal.",
        "flow_signal_expired_generic": "Signal expired or invalid. Cannot proceed.",
        "flow_fetch_signal_fail": "Failed to load signal (expired or not found). Please check the channel for the latest signal.",
        "flow_signal_expired_deeplink": "This signal has expired. Please go back to the channel for the latest signal.",
        "start_prompt": "Bot is ready. Go to the public channel and click \"One-Click Copy\" to start.\n\nCommand: /balance — Check balance",
        "flow_insufficient_balance": "Order failed: Insufficient balance. Please top up.",
        "flow_private_only_alert": "Please use this in Direct Message.",
        "flow_unsupported_lang": "Unsupported language",
        "flow_leverage_invalid_alert": "Invalid leverage",
        "flow_private_operate": "Please complete this in Direct Message.",
        "flow_platform_not_configured": "PLATFORM_API_BASE_URL is not configured. Cannot place order.",
        "flow_channel_hint": "Please click the button in the channel message and complete the flow in DM with the bot.",
        "cmd_balance_private": "Please use this command in Direct Message.",

        # Exchange info validation
        "exinfo_unavailable": "Unable to fetch symbol limits. Please try again later.",
        "lev_too_high": "Leverage exceeds limit (Max {max_lev}x). Please re-enter.",
        "qty_out_of_range": "Order quantity out of range ({min_qty} - {max_qty}). Please adjust amount or leverage.",
        "lev_set_failed": "Leverage setup failed. Please try again later.",
        "notional_too_high": "Notional value exceeds limit (Max {max_notional}). Please lower leverage or amount.",

        # API errors (platform)
        "api_err_generic": "API Error",
        "api_err_unknown": "API Error",
        "api_err_401": "Unauthorized",
        "api_err_500": "Internal System Error",
        "api_err_501": "System Busy",
        "api_err_506": "Unknown Request Source",
        "api_err_510": "Request Too Frequent",
        "api_err_511": "API Access Forbidden",
        "api_err_513": "Invalid Request Time",
        "api_err_514": "Duplicate Request",
        "api_err_515": "Access Denied",
        "api_err_600": "Invalid Parameters",
        "api_err_1002": "Unsupported Trading Pair",
        "api_err_1003": "Unsupported Coin",
        "api_err_1005": "Insufficient Balance",
        "api_err_2001": "Trading Suspended",
        "api_err_2021": "Market Data Error",
        "api_err_2022": "Market Data Outdated",
        "api_err_2023": "Trading Prohibited",
        "api_err_100012": "Insufficient Margin",
        "api_err_100014": "Order Does Not Exist",
        "api_err_100019": "No Assets",
        "api_err_100051": "Leverage Exceeds Limit",
        "api_err_200008": "Contract Does Not Exist",
        "api_err_200009": "Unsupported Coin for Futures Trading",
        "api_err_200014": "Order Cancellation Failed: User Mismatch",
        "api_err_200015": "Insufficient User Assets",

        # Order errors
        "order_failed": "❌ Order Failed",
        "reason_line": "Reason: {reason}",
        "unknown_error": "Unknown Error",
        "order_delegating": "🚀 Order Processing...",
        "order_delegated_ok": "✅ Order Successful!\nOrder ID: <code>{order_id}</code>\nPosition value: <code>{position_value}</code> USDT\nStatus: <b>Order Successful</b>",

        # Open orders
        "orders_loading": "Querying...",
        "orders_title": "📌 Current Open Orders",
        "orders_empty": "No Open Orders",
        "orders_page": "Page {page}/{pages} (Total: {total})",
        "orders_cancel_hint": "Click the Order ID below to cancel the order:",
        "orders_refresh": "Refresh",
        "orders_prev": "Previous Page",
        "orders_next": "Next Page",
        "orders_cancel_all_btn": "Cancel All",
        "orders_cancel_all_confirm_btn": "Confirm Cancel All",
        "orders_cancel_all_back_btn": "Back",
        "orders_cancel_all_alert": "⚠️ All open orders will be cancelled.\n\nIf you’re sure, tap “Confirm cancel all” again.",
        "orders_cancel_all_done": "All orders have been cancelled (Total: {count})",
        "orders_cancel_all_partial": "Partially cancelled ({ok}/{total} orders). Please click \"Refresh\" to confirm.",
        "orders_cancel_all_none": "No cancellable orders found.",
        "orders_cancel_all_fail": "Cancel All failed: {reason}",
        "orders_snapshot_expired": "List expired (over {ttl} seconds). Please click \"Refresh\" before cancelling.",
        "orders_order_gone": "Order no longer exists or has been filled. Please click \"Refresh\" to update.",
        "orders_cancel_ok": "Cancellation successful",
        "orders_cancel_fail": "Cancellation failed: {reason}",
        "orders_item": (
            "💡 <b>Order ID</b>: <code>{order_id}</code>\n"
            "Trading Pair: <code>{symbol}</code>\n"
            "Side: {side}\n"
            "Leverage: <code>{leverage}</code>x\n"
            "Order Price: <code>{price}</code>\n"
            "Margin: <code>{margin}</code> USDT\n"
            "Time: <code>{create_time}</code>"
        ),

        # Positions
        "positions_loading": "Querying...",
        "positions_title": "📌 Current Positions",
        "positions_empty": "No open positions.",
        "positions_page": "Page {page}/{pages} (Total: {total})",
        "positions_refresh": "Refresh",
        "positions_prev": "Previous Page",
        "positions_next": "Next Page",
        "positions_item": (
            "💡 <b>Trading Pair</b>: <code>{symbol}</code>\n"
            "Side: {side}\n"
            "Position Value: <code>{holding_value}</code> {settle}\n"
            "Entry Price: <code>{avg_price}</code>\n"
            "Mark Price: <code>{mark_price}</code>\n"
            "Liquidation Price: <code>{liq_price}</code>\n"
            "Margin: <code>{margin}</code> {settle}\n"
            "Unrealized PnL: <code>{pnl}</code> {settle} ({pnl_pct}%){tp_sl_line}"
        ),
        "tp_sl_ratio_full": "Close All",
        "tp_sl_ratio_partial": "{pct}%",
        "positions_tp_sl_line": "\nTake Profit: <code>{tp}</code>  Stop Loss: <code>{sl}</code>",
        "positions_close_btn": "Close {symbol}",
        "positions_close_all_btn": "One-Click Close",
        "positions_close_all_alert": "⚠️ All open positions will be closed.\n\nClick \"Confirm One-Click Close\" again to proceed.",
        "positions_close_all_confirm_btn": "Confirm One-Click Close",
        "positions_close_all_back_btn": "Back",
        "positions_close_hint": "Click the Close button below to close the position:",
        "positions_close_ok": "Position closed successfully",
        "positions_close_fail": "Failed to close position: {reason}",
        "positions_close_all_done": "All positions have been closed (Total: {count})",
        "positions_close_all_partial": "Partially closed ({ok}/{total} positions). Please click Refresh to confirm.",
        "positions_close_all_none": "No positions available to close.",
        "positions_close_all_fail": "One-Click Close failed: {reason}",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    table = TRANSLATIONS.get(lang) or TRANSLATIONS["en"]
    template = table.get(key) or TRANSLATIONS["en"].get(key) or key
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

