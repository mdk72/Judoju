# TIGER ETF 화이트리스트 및 카테고리 정의

TIGER_ETF_UNIVERSE = {
    "국내지수": [
        {"ticker": "069500", "name": "KODEX 200"}, # KODEX지만 유동성 상징성으로 포함 가능성 고려 (사용자 TIGER 선호시 102110)
        {"ticker": "102110", "name": "TIGER 200"},
        {"ticker": "233740", "name": "TIGER 코스닥150레버리지"},
        {"ticker": "153130", "name": "TIGER 단기통안채"},
    ],
    "해외지수": [
        {"ticker": "133690", "name": "TIGER 미국나스닥100"},
        {"ticker": "360750", "name": "TIGER 미국테크TOP10 INDXX"},
        {"ticker": "143850", "name": "TIGER 미국S&P500선물(H)"},
        {"ticker": "453870", "name": "TIGER 인도Nifty50"},
    ],
    "섹터/테마": [
        {"ticker": "139230", "name": "TIGER 2차전지테마"},
        {"ticker": "466920", "name": "TIGER 미국필라델피아반도체나스닥"},
        {"ticker": "305540", "name": "TIGER 2차전지인버스(합성)"},
        {"ticker": "227540", "name": "TIGER 헬스케어"},
        {"ticker": "217770", "name": "TIGER 화장품"},
    ],
    "현금흐름/배당": [
        {"ticker": "452250", "name": "TIGER 미국배당다우존스"},
        {"ticker": "452260", "name": "TIGER 미국배당프리미엄다우존스"},
        {"ticker": "479010", "name": "TIGER 미국테크TOP10+10%프리미엄"},
    ],
    "안전/대안": [
        {"ticker": "458250", "name": "TIGER 미국채10년선물"},
        {"ticker": "233160", "name": "TIGER 미국S&P500레버리지(합성H)"},
        {"ticker": "138530", "name": "TIGER 금은선물(H)"},
        {"ticker": "139280", "name": "TIGER 구리선물(H)"},
    ]
}
