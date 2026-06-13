import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import io
import json
import base64
import datetime
import requests
import warnings
warnings.filterwarnings('ignore')

try:
    import japanize_matplotlib
except:
    pass

st.set_page_config(page_title="Market Regime", page_icon="📊", layout="wide")
st.title("📊 MARKET REGIME SCORER")
st.caption("週次市場環境スコア — スイングトレード判断ツール")

CSV_PATH = 'data/regime_history.csv'

# GitHub設定
GITHUB_TOKEN = st.secrets.get('github_token', '')
GITHUB_REPO  = st.secrets.get('github_repo', '')
GITHUB_API   = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{CSV_PATH}'

INDICATORS = {
    'DXY'    : 'ドル指数',
    'TLT'    : '米長期国債ETF',
    'HYG'    : 'ハイイールド債ETF',
    'BAA_AAA': 'クレジットスプレッド',
    'Y10_Y2' : '長短金利差(10Y-2Y)',
    'SCREEN' : 'スクリーニング抽出数前週比',
}

SHORT_INDICATORS = {
    'AD_LINE': 'ADライン（騰落線）',
    'NH_NL'  : 'ニューハイズ／ニューロウズ',
}

BULLISH = {
    'DXY'    : '↓',
    'TLT'    : '↑',
    'HYG'    : '↑',
    'BAA_AAA': '↓',
    'Y10_Y2' : '↑',
    'SCREEN' : '↑',
    'AD_LINE': '↑',
    'NH_NL'  : '↑',
}

def calc_score(values):
    total = 0
    for key, val in values.items():
        if key not in BULLISH: continue
        if val == BULLISH[key]: total += 1
        elif val == '→':        total += 0
        else:                    total -= 1
    return round((total + 6) / 12 * 100)

def calc_short_score(values):
    total = 0
    for key, val in values.items():
        if key not in BULLISH: continue
        if val == BULLISH[key]: total += 1
        elif val == '→':        total += 0
        else:                    total -= 1
    return round((total + 2) / 4 * 100)

def get_regime(score):
    if score >= 80: return '🟢 RISK-ON',      '#00ff88'
    if score >= 60: return '🔵 CONSTRUCTIVE',  '#4ecdc4'
    if score >= 40: return '🟡 NEUTRAL',       '#ffd93d'
    if score >= 20: return '🟠 CAUTIOUS',      '#e17055'
    return              '🔴 RISK-OFF',         '#ff6b6b'

def get_short_regime(score):
    if score >= 80: return '🟢 強い', '#00ff88'
    if score >= 40: return '🟡 中立', '#ffd93d'
    return              '🔴 弱い', '#ff6b6b'

# ============================================================
#  GitHub 読み書き
# ============================================================
def github_load():
    """GitHubからCSVを読み込む"""
    if not GITHUB_TOKEN:
        return pd.DataFrame(), None
    try:
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        r = requests.get(GITHUB_API, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            sha = data['sha']
            df = pd.read_csv(io.StringIO(content))
            return df, sha
        else:
            return pd.DataFrame(), None
    except Exception as e:
        st.error(f'読み込みエラー: {e}')
        return pd.DataFrame(), None

def github_save(df, sha=None):
    """GitHubにCSVを書き込む"""
    if not GITHUB_TOKEN:
        st.error('GitHubトークンが設定されていません')
        return False
    try:
        csv_str = df.to_csv(index=False, encoding='utf-8-sig')
        content_b64 = base64.b64encode(csv_str.encode('utf-8')).decode('utf-8')
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        payload = {
            'message': f'Update regime_history {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}',
            'content': content_b64,
        }
        if sha:
            payload['sha'] = sha
        r = requests.put(GITHUB_API, headers=headers, data=json.dumps(payload), timeout=10)
        if r.status_code in (200, 201):
            return True
        else:
            st.error(f'保存エラー: {r.status_code} {r.text[:200]}')
            return False
    except Exception as e:
        st.error(f'保存エラー: {e}')
        return False

def save_record(date, values, short_values, score, short_score, memo):
    df, sha = github_load()
    row = {'date': date, 'score': score, 'short_score': short_score, 'memo': memo}
    for k, v in values.items():       row[k] = v
    for k, v in short_values.items(): row[k] = v
    new_row = pd.DataFrame([row])
    if len(df) > 0:
        df = df[df['date'] != date]
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df = df.sort_values('date')
    return github_save(df, sha)

# ============================================================
#  タブ
# ============================================================
tab1, tab2, tab3 = st.tabs(['📝 今週の評価', '📈 推移グラフ', '📋 履歴一覧'])

with tab1:
    st.subheader('📝 今週の市場環境を入力')
    today = datetime.date.today()
    days_since_sat = (today.weekday() - 5) % 7
    last_sat = today - datetime.timedelta(days=days_since_sat)
    input_date = st.date_input('基準日', value=last_sat)
    st.divider()

    cols_map = {
        'DXY'    : ('DXY（ドル指数）',          '↓が株式に追い風'),
        'TLT'    : ('TLT（米長期国債ETF）',      '↑が株式に追い風'),
        'HYG'    : ('HYG（ハイイールド債ETF）',  '↑が株式に追い風'),
        'BAA_AAA': ('クレジットスプレッド',       '↓が株式に追い風'),
        'Y10_Y2' : ('長短金利差（10Y-2Y）',       '↑が株式に追い風'),
        'SCREEN' : ('スクリーニング抽出数前週比',  '↑が株式に追い風'),
    }
    short_map = {
        'AD_LINE': ('ADライン（騰落線）',         '上昇中なら市場全体が強い'),
        'NH_NL'  : ('ニューハイズ／ニューロウズ',  'ニューハイ優勢なら強い'),
    }

    st.subheader('📊 メイン指標（中長期）')
    values = {}
    for key, (label, hint) in cols_map.items():
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f'**{label}**')
            st.caption(hint)
        with c2:
            values[key] = st.radio(label, ['↑','→','↓'], horizontal=True,
                                    key=f'radio_{key}', label_visibility='collapsed')

    st.divider()
    st.subheader('⚡ 短期指標')
    short_values = {}
    for key, (label, hint) in short_map.items():
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f'**{label}**')
            st.caption(hint)
        with c2:
            short_values[key] = st.radio(label, ['↑','→','↓'], horizontal=True,
                                         key=f'radio_{key}', label_visibility='collapsed')

    st.divider()
    memo = st.text_area('📝 メモ（任意）', placeholder='今週の相場所感など...', height=80)

    score       = calc_score(values)
    short_score = calc_short_score(short_values)
    regime_label, regime_color = get_regime(score)
    short_label,  short_color  = get_short_regime(short_score)

    st.divider()
    st.subheader('📊 今週のスコア')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('メインスコア', f'{score}点')
    col2.markdown(f'<h3 style="color:{regime_color}">{regime_label}</h3>', unsafe_allow_html=True)
    col3.metric('短期スコア', f'{short_score}点')
    col4.markdown(f'<h3 style="color:{short_color}">{short_label}</h3>', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="margin-bottom:4px"><small style="color:#aaa">メイン</small></div>
    <div style="background:#1a1a1a;border-radius:10px;padding:4px;margin-bottom:12px">
        <div style="background:{regime_color};width:{score}%;height:24px;border-radius:8px;"></div>
    </div>
    <div style="margin-bottom:4px"><small style="color:#aaa">短期</small></div>
    <div style="background:#1a1a1a;border-radius:10px;padding:4px;">
        <div style="background:{short_color};width:{short_score}%;height:16px;border-radius:8px;"></div>
    </div>
    ''', unsafe_allow_html=True)

    st.subheader('内訳')
    st.caption('── メイン指標 ──')
    for key, (label, hint) in cols_map.items():
        v = values[key]; b = BULLISH[key]
        if v == b:      icon='✅ +1'; color='#00ff88'
        elif v == '→': icon='➡️  0'; color='#aaaaaa'
        else:           icon='❌ -1'; color='#ff6b6b'
        st.markdown(f'<span style="color:{color}"><b>{icon}</b></span>　{label}：{v}', unsafe_allow_html=True)
    st.caption('── 短期指標 ──')
    for key, (label, hint) in short_map.items():
        v = short_values[key]; b = BULLISH[key]
        if v == b:      icon='✅ +1'; color='#00ff88'
        elif v == '→': icon='➡️  0'; color='#aaaaaa'
        else:           icon='❌ -1'; color='#ff6b6b'
        st.markdown(f'<span style="color:{color}"><b>{icon}</b></span>　{label}：{v}', unsafe_allow_html=True)

    st.divider()
    if st.button('💾 記録を保存', type='primary', use_container_width=True):
        with st.spinner('GitHubに保存中...'):
            ok = save_record(str(input_date), values, short_values, score, short_score, memo)
        if ok:
            st.success(f'✅ {input_date} のスコア {score}点（短期:{short_score}点）を保存しました！')
            st.balloons()

with tab2:
    st.subheader('📈 スコア推移')
    hist, _ = github_load()

    if len(hist) == 0:
        st.info('まだ記録がありません。「今週の評価」タブで入力してください。')
    else:
        hist['date']  = pd.to_datetime(hist['date'])
        hist['score'] = pd.to_numeric(hist['score'], errors='coerce')
        hist = hist.sort_values('date')

        fig, ax = plt.subplots(figsize=(max(12, len(hist)*0.8), 5), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')
        ax.tick_params(colors='#aaaaaa', labelsize=9)
        ax.grid(True, alpha=0.12, color='#444444')
        for spine in ax.spines.values():
            spine.set_color('#2a2a2a')
        ax.axhspan(80,100, alpha=0.08, color='#00ff88')
        ax.axhspan(60, 80, alpha=0.08, color='#4ecdc4')
        ax.axhspan(40, 60, alpha=0.08, color='#ffd93d')
        ax.axhspan(20, 40, alpha=0.08, color='#e17055')
        ax.axhspan(0,  20, alpha=0.08, color='#ff6b6b')
        for y, label, color in [
            (90,'RISK-ON','#00ff88'),(70,'CONSTRUCTIVE','#4ecdc4'),
            (50,'NEUTRAL','#ffd93d'),(30,'CAUTIOUS','#e17055'),(10,'RISK-OFF','#ff6b6b')]:
            ax.text(0.01, y, label, transform=ax.get_yaxis_transform(),
                    color=color, fontsize=8, alpha=0.6, va='center')

        colors_pts = [get_regime(s)[1] for s in hist['score']]
        ax.plot(hist['date'], hist['score'], color='white', linewidth=2.0,
                marker='o', markersize=6, zorder=3, label='メインスコア')
        for x, y, c in zip(hist['date'], hist['score'], colors_pts):
            ax.scatter(x, y, color=c, s=60, zorder=4)
            ax.annotate(f'{int(y)}', xy=(x, y), xytext=(0, 8),
                        textcoords='offset points', color=c,
                        fontsize=8, fontweight='bold', ha='center')
        if 'short_score' in hist.columns:
            hist['short_score'] = pd.to_numeric(hist['short_score'], errors='coerce')
            ax.plot(hist['date'], hist['short_score'], color='#ffd93d', linewidth=1.5,
                    marker='s', markersize=4, linestyle='--', label='短期スコア', zorder=2)
        ax.set_ylim(0, 105)
        ax.set_ylabel('スコア', color='#aaaaaa', fontsize=10)
        ax.set_title('Market Regime スコア推移', color='white', fontsize=12, fontweight='bold')
        ax.legend(facecolor='#1a1a1a', labelcolor='white', fontsize=9)
        plt.xticks(rotation=30)
        plt.tight_layout()
        st.pyplot(fig)

        st.subheader('📊 各指標の推移')
        all_keys = list(INDICATORS.keys()) + list(SHORT_INDICATORS.keys())
        indicator_cols = [k for k in all_keys if k in hist.columns]
        all_indicators = {**INDICATORS, **SHORT_INDICATORS}
        if indicator_cols:
            fig2, axes = plt.subplots(len(indicator_cols), 1,
                                      figsize=(max(12, len(hist)*0.8), len(indicator_cols)*1.8),
                                      facecolor='#0d1117')
            if len(indicator_cols) == 1:
                axes = [axes]
            for ax2, key in zip(axes, indicator_cols):
                ax2.set_facecolor('#0d1117')
                ax2.tick_params(colors='#aaaaaa', labelsize=8)
                for spine in ax2.spines.values():
                    spine.set_color('#2a2a2a')
                vals = hist[key].fillna('→')
                colors_ind = []
                for v in vals:
                    b = BULLISH[key]
                    if v == b:      colors_ind.append('#00ff88')
                    elif v == '→': colors_ind.append('#aaaaaa')
                    else:           colors_ind.append('#ff6b6b')
                ax2.bar(range(len(hist)), [1]*len(hist), color=colors_ind, alpha=0.8)
                ax2.set_yticks([])
                ax2.set_xticks(range(len(hist)))
                ax2.set_xticklabels([d.strftime('%m/%d') for d in hist['date']],
                                    rotation=30, fontsize=8, color='#aaaaaa')
                label = all_indicators.get(key, key)
                is_short = key in SHORT_INDICATORS
                ax2.set_title(f'{"⚡ " if is_short else ""}{label}',
                              color='#ffd93d' if is_short else '#aaaaaa', fontsize=9, pad=4)
            plt.tight_layout()
            st.pyplot(fig2)

        st.subheader('📅 月次平均スコア')
        hist['month'] = hist['date'].dt.to_period('M').astype(str)
        monthly = hist.groupby('month')['score'].mean().round(1).reset_index()
        monthly.columns = ['月', '平均スコア']
        st.dataframe(monthly.iloc[::-1].reset_index(drop=True), use_container_width=True)

with tab3:
    st.subheader('📋 履歴一覧')
    hist2, sha2 = github_load()
    if len(hist2) == 0:
        st.info('まだ記録がありません。')
    else:
        hist2 = hist2.sort_values('date', ascending=False).reset_index(drop=True)
        hist2.index += 1
        def color_score_cell(val):
            try:
                v = int(val); rl, rc = get_regime(v)
                return f'background-color:{rc}22;color:{rc};font-weight:bold'
            except:
                return ''
        st.dataframe(
            hist2.style.map(color_score_cell, subset=['score']),
            use_container_width=True, height=500
        )
        with st.expander('🗑️ 記録を削除'):
            del_date = st.selectbox('削除する日付', hist2['date'].tolist())
            if st.button('削除する', type='secondary'):
                df_del, sha_del = github_load()
                df_del = df_del[df_del['date'] != del_date]
                if github_save(df_del, sha_del):
                    st.success(f'{del_date} の記録を削除しました')
                    st.rerun()

st.caption(f'最終更新: {pd.Timestamp.now().strftime("%Y/%m/%d %H:%M")}')
