from io import StringIO
from pathlib import Path
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


def download(showFp='1'):
    showFp_names = {
        '': '全報告数',
        '2': '定点数',
        '1': '定点当たり報告数',
    }
    url = 'https://survey.tmiph.metro.tokyo.lg.jp/epidinfo/weeklyhc.do'
    payloads = {
        'periodOffset': '1',
        'val(prefCode)': '13',
        'val(hcCode)': '00',
        'val(epidCode)': '',
        'val(refMode)': '',
        'val(refYear)': '',
        'val(showFp)': showFp,
        'val(year)': 2999,
        'val(week)': 53,
    }

    response = requests.post(url, data=payloads)
    if not response.ok:
        return False
    soup = BeautifulSoup(response.text, features="lxml")

    # 年、週番号
    year = soup.select_one("select[name='val(year)'] > option[selected]").text
    week_num = soup.select_one("select[name='val(week)'] > option[selected]").text

    # 対象期間
    target_range = soup.find('td', string=re.compile('対象期間')).text
    mob = re.search(r"対象期間：\s+(\d+)年(\d+)月(\d+)日 - (\d+)年(\d+)月(\d+)日", target_range)
    if mob:
        start_date = '{:0>4s}-{:0>2s}-{:0>2s}'.format(*mob.groups()[:3])
        end_date = '{:0>4s}-{:0>2s}-{:0>2s}'.format(*mob.groups()[3:])
    else:
        start_date, end_date = None, None

    # データ部
    table = None
    for tag in soup.select_one('td.epidNameCell').parents:
        if tag.name == 'table':
            table = tag
            break
    df = (
        pd.read_html(StringIO(str(table).replace('<br/>', '')), header=0)[0]
        .rename(columns={'保健所／疾病名': '保健所'})
        .query("保健所 != '合計' and 保健所 != '報告数/定点数'")
    )
    cols = list(df.columns)
    df = (
        df.assign(**{'年': year, '週番号': week_num, '開始日': start_date, '終了日': end_date})
        [['年', '週番号', '開始日', '終了日'] + cols]
        .rename(columns={
            '新型コロナウイルス感染症／COVID|19': '新型コロナウイルス感染症／COVID-19',
            'ヘルパンギ｜ナ': 'ヘルパンギーナ',
            'COVID|19入院': 'COVID-19入院',
        })
    )

    # 過去データと連結
    filepath = Path(__file__).parent / f'{showFp_names[showFp]}.csv'
    df_all = pd.concat([
        pd.read_csv(filepath, dtype=str),
        df
    ]).drop_duplicates(subset=['年', '開始日', '保健所'])
    df_all.to_csv(filepath, index=False)


if __name__ == "__main__":
    # 全報告数
    download('')
    # 定点数
    download('2')
