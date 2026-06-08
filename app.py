import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import datetime
import warnings
warnings.filterwarnings('ignore')


try:
    import japanize_matplotlib
except:
    pass

st.set_page_config(page_title="Market Regime", page_icon="📊", layout="wide")
st.title("📊 MARKET REGIME SCORER")
st.caption("週次市場環境スコア — スイングトレード判断ツール")

HISTORY_PATH = 'data/regime_history.csv'

INDICATORS = {
    'DXY'   : 'ドル指数',
    'TLT'   : '米長期国債ETF',
    'HYG'   : 'ハイイールド債ETF',
    'BAA_AAA': 'クレジットスプレッド',
    'Y10_Y2': '長短金利差(10Y-2Y)',
    'SCREEN': 'スクリーニング抽出数前週比',
}

BULLISH = {
    'DXY'   : '↓',
    'TLT'   : '↑',
    'HYG'   : '↑',
    'BAA_AAA': '↓',
    'Y10_Y2': '↑',
    'SCREEN': '↑',
}

def calc_score(values):
    total = 0
    for key, val in values.items():
        bullish = BULLISH[key]
        if val == bullish:
            total += 1
        elif val == '→':
            total += 0
        else:
            total -= 1
    # -6〜+6 を 0〜100に換算
    return round((total + 6) / 12 * 100)

def get_regime(score):
    if score >= 80: return '🟢 RISK-ON',      '#00ff88'
    if score >= 60: return '🔵 CONSTRUCTIVE',  '#4ecdc4'
    if score >= 40: return '🟡 NEUTRAL',       '#ffd93d'
    if score >= 20: return '🟠 CAUTIOUS',      '#e17055'
    return              '🔴 RISK-OFF',         '#ff6b6b'

def load_history():
    if os.path.exists(HISTORY_PATH):
        return pd.read_csv(HISTORY_PATH)
    return pd.DataFrame()

def save_record(date, values, score, memo):
    os.makedirs('data', exist_ok=True)
    row = {'date': date, 'score': score, 'memo': memo}
    for k, v in values.items():
        row[k] = v
    new_row = pd.DataFrame([row])
    if os.path.exists(HISTORY_PATH):
        hist = pd.read_csv(HISTORY_PATH)
        hist = hist[hist['date'] != date]
        hist = pd.concat([hist, new_row], ignore_index=True)
    else:
        hist = new_row
    hist = hist.sort_values('date')
    hist.to_csv(HISTORY_PATH, index=False, encoding='utf-8-sig')

# ============================================================
#  タブ
# ============================================================
tab1, tab2, tab3 = st.tabs(['📝 今週の評価', '📈 推移グラフ', '📋 履歴一覧'])

with tab1:
    st.subheader('📝 今週の市場環境を入力')

    today = datetime.date.today()
    # 直近土曜日を基準日にする
    days_since_sat = (today.weekday() - 5) % 7
    last_sat = today - datetime.timedelta(days=days_since_sat)
    input_date = st.date_input('基準日', value=last_sat)

    st.divider()

    values = {}
    cols_map = {
        'DXY'   : ('DXY（ドル指数）',           '↓が株式に追い風'),
        'TLT'   : ('TLT（米長期国債ETF）',       '↑が株式に追い風'),
        'HYG'   : ('HYG（ハイイールド債ETF）',   '↑が株式に追い風'),
        'BAA_AAA': ('クレジットスプレッド',        '↓が株式に追い風'),
        'Y10_Y2': ('長短金利差（10Y-2Y）',        '↑が株式に追い風'),
        'SCREEN': ('スクリーニング抽出数前週比',   '↑が株式に追い風'),
    }

    for key, (label, hint) in cols_map.items():
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f'**{label}**')
            st.caption(hint)
        with c2:
            val = st.radio(
                label,
                options=['↑', '→', '↓'],
                horizontal=True,
                key=f'radio_{key}',
                label_visibility='collapsed'
            )
        values[key] = val

    st.divider()
    memo = st.text_area('📝 メモ（任意）', placeholder='今週の相場所感など...', height=80)

    score = calc_score(values)
    regime_label, regime_color = get_regime(score)

    st.divider()
    st.subheader('📊 今週のスコア')

    col1, col2, col3 = st.columns(3)
    col1.metric('スコア', f'{score}点')
    col2.markdown(f'<h2 style="color:{regime_color}">{regime_label}</h2>', unsafe_allow_html=True)

    # スコアバー
    bar_col = regime_color
    st.markdown(f'''
    <div style="background:#1a1a1a;border-radius:10px;padding:4px;">
        <div style="background:{bar_col};width:{score}%;height:24px;border-radius:8px;"></div>
    </div>
    ''', unsafe_allow_html=True)
    st.caption(f'{score}/100')

    # 内訳
    st.subheader('内訳')
    for key, (label, hint) in cols_map.items():
        v = values[key]
        b = BULLISH[key]
        if v == b:
            icon = '✅ +1'
            color = '#00ff88'
        elif v == '→':
            icon = '➡️  0'
            color = '#aaaaaa'
        else:
            icon = '❌ -1'
            color = '#ff6b6b'
        st.markdown(f'<span style="color:{color}"><b>{icon}</b></span>　{label}：{v}', unsafe_allow_html=True)

    st.divider()
    if st.button('💾 記録を保存', type='primary', use_container_width=True):
        save_record(str(input_date), values, score, memo)
        st.success(f'✅ {input_date} のスコア {score}点 を保存しました！')
        st.balloons()

with tab2:
    st.subheader('📈 スコア推移')
    hist = load_history()

    if len(hist) == 0:
        st.info('まだ記録がありません。「今週の評価」タブで入力してください。')
    else:
        hist['date']  = pd.to_datetime(hist['date'])
        hist['score'] = pd.to_numeric(hist['score'], errors='coerce')
        hist = hist.sort_values('date')

        # スコア推移グラフ
        fig, ax = plt.subplots(figsize=(max(12, len(hist)*0.8), 5), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')
        ax.tick_params(colors='#aaaaaa', labelsize=9)
        ax.grid(True, alpha=0.12, color='#444444')
        for spine in ax.spines.values():
            spine.set_color('#2a2a2a')

        # 背景色ゾーン
        ax.axhspan(80, 100, alpha=0.08, color='#00ff88')
        ax.axhspan(60,  80, alpha=0.08, color='#4ecdc4')
        ax.axhspan(40,  60, alpha=0.08, color='#ffd93d')
        ax.axhspan(20,  40, alpha=0.08, color='#e17055')
        ax.axhspan(0,   20, alpha=0.08, color='#ff6b6b')

        # ゾーンラベル
        for y, label, color in [
            (90, 'RISK-ON',      '#00ff88'),
            (70, 'CONSTRUCTIVE', '#4ecdc4'),
            (50, 'NEUTRAL',      '#ffd93d'),
            (30, 'CAUTIOUS',     '#e17055'),
            (10, 'RISK-OFF',     '#ff6b6b'),
        ]:
            ax.text(0.01, y, label, transform=ax.get_yaxis_transform(),
                    color=color, fontsize=8, alpha=0.6, va='center')

        # ライン
        colors_pts = []
        for s in hist['score']:
            rl, rc = get_regime(s)
            colors_pts.append(rc)

        ax.plot(hist['date'], hist['score'], color='white', linewidth=2.0,
                marker='o', markersize=6, zorder=3)
        for i, (x, y, c) in enumerate(zip(hist['date'], hist['score'], colors_pts)):
            ax.scatter(x, y, color=c, s=60, zorder=4)
            ax.annotate(f'{int(y)}', xy=(x, y), xytext=(0, 8),
                        textcoords='offset points', color=c,
                        fontsize=8, fontweight='bold', ha='center')

        ax.set_ylim(0, 105)
        ax.set_ylabel('スコア', color='#aaaaaa', fontsize=10)
        ax.set_title('Market Regime スコア推移', color='white', fontsize=12, fontweight='bold')
        plt.xticks(rotation=30)
        plt.tight_layout()
        st.pyplot(fig)

        # 各指標の推移
        st.subheader('📊 各指標の推移')
        indicator_cols = [k for k in INDICATORS.keys() if k in hist.columns]
        if indicator_cols:
            fig2, axes = plt.subplots(len(indicator_cols), 1,
                                      figsize=(max(12, len(hist)*0.8), len(indicator_cols)*1.8),
                                      facecolor='#0d1117')
            if len(indicator_cols) == 1:
                axes = [axes]
            for ax, key in zip(axes, indicator_cols):
                ax.set_facecolor('#0d1117')
                ax.tick_params(colors='#aaaaaa', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('#2a2a2a')
                vals = hist[key].fillna('→')
                colors_ind = []
                for v in vals:
                    b = BULLISH[key]
                    if v == b:      colors_ind.append('#00ff88')
                    elif v == '→': colors_ind.append('#aaaaaa')
                    else:           colors_ind.append('#ff6b6b')
                ax.bar(range(len(hist)), [1]*len(hist), color=colors_ind, alpha=0.8)
                ax.set_yticks([])
                ax.set_xticks(range(len(hist)))
                ax.set_xticklabels([d.strftime('%m/%d') for d in hist['date']],
                                   rotation=30, fontsize=8, color='#aaaaaa')
                ax.set_title(INDICATORS[key], color='#aaaaaa', fontsize=9, pad=4)
            plt.tight_layout()
            st.pyplot(fig2)

        # 月次集計
        st.subheader('📅 月次平均スコア')
        hist['month'] = hist['date'].dt.to_period('M').astype(str)
        monthly = hist.groupby('month')['score'].mean().round(1).reset_index()
        monthly.columns = ['月', '平均スコア']
        st.dataframe(monthly.iloc[::-1].reset_index(drop=True), use_container_width=True)

with tab3:
    st.subheader('📋 履歴一覧')
    hist2 = load_history()
    if len(hist2) == 0:
        st.info('まだ記録がありません。')
    else:
        hist2 = hist2.sort_values('date', ascending=False).reset_index(drop=True)
        hist2.index += 1

        def color_score_cell(val):
            try:
                v = int(val)
                rl, rc = get_regime(v)
                return f'background-color:{rc}22;color:{rc};font-weight:bold'
            except:
                return ''

        st.dataframe(
            hist2.style.map(color_score_cell, subset=['score']),
            use_container_width=True,
            height=500
        )

        # 削除機能
        with st.expander('🗑 記録を削除'):
            del_date = st.selectbox('削除する日付', hist2['date'].tolist())
            if st.button('削除する', type='secondary'):
                h = pd.read_csv(HISTORY_PATH)
                h = h[h['date'] != del_date]
                h.to_csv(HISTORY_PATH, index=False, encoding='utf-8-sig')
                st.success(f'{del_date} の記録を削除しました')
                st.rerun()

st.caption(f'最終更新: {pd.Timestamp.now().strftime("%Y/%m/%d %H:%M")}')
