"""決まり手のローマ字 → 日本語。"""

KIMARITE = {
    "abisetaoshi": "浴びせ倒し", "amiuchi": "網打ち", "ashitori": "足取り", "chongake": "ちょん掛け",
    "isamiashi": "勇み足", "gasshohineri": "合掌捻り", "hatakikomi": "叩き込み",
    "hikiotoshi": "引き落とし", "hikkake": "引っ掛け", "ipponzeoi": "一本背負い", "izori": "居反り",
    "kainahineri": "腕捻り", "kakenage": "掛け投げ", "kakezori": "掛け反り", "kawazugake": "河津掛け",
    "kekaeshi": "蹴返し", "ketaguri": "蹴手繰り", "kimedashi": "極め出し", "kimetaoshi": "極め倒し",
    "kirikaeshi": "切り返し", "komatasukui": "小股掬い", "koshikudake": "腰砕け", "koshinage": "腰投げ",
    "kotehineri": "小手捻り", "kotenage": "小手投げ", "kozumatori": "小褄取り", "kubihineri": "首捻り",
    "kubinage": "首投げ", "mitokorozeme": "三所攻め", "nichonage": "二丁投げ", "nimaigeri": "二枚蹴り",
    "okuridashi": "送り出し", "okurigake": "送り掛け", "okurihikiotoshi": "送り引き落とし",
    "okurinage": "送り投げ", "okuritaoshi": "送り倒し", "okuritsuridashi": "送り吊り出し",
    "okuritsuriotoshi": "送り吊り落とし", "omata": "大股", "oshidashi": "押し出し",
    "oshitaoshi": "押し倒し", "sabaori": "鯖折り", "sakatottari": "逆とったり", "shitatedashinage": "下手出し投げ",
    "shitatehineri": "下手捻り", "shitatenage": "下手投げ", "sotogake": "外掛け", "sotokomata": "外小股",
    "sotomuso": "外無双", "sototasukizori": "外たすき反り", "sukuinage": "掬い投げ", "susoharai": "裾払い",
    "susotori": "裾取り", "tasukizori": "たすき反り", "tokkurinage": "徳利投げ", "tottari": "とったり",
    "tsukaminage": "つかみ投げ", "tsukidashi": "突き出し", "tsukiotoshi": "突き落とし", "tsukitaoshi": "突き倒し",
    "tsukite": "つき手", "tsukihiza": "つきひざ", "fumikoshi": "踏み越し",
    "tsumatori": "褄取り", "tsuridashi": "吊り出し", "tsuriotoshi": "吊り落とし", "uchigake": "内掛け",
    "uchimuso": "内無双", "uwatedashinage": "上手出し投げ", "uwatehineri": "上手捻り", "uwatenage": "上手投げ",
    "watashikomi": "渡し込み", "yaguranage": "櫓投げ", "yobimodoshi": "呼び戻し", "yorikiri": "寄り切り",
    "yoritaoshi": "寄り倒し", "zubuneri": "ずぶねり", "hansoku": "反則", "fusen": "不戦",
    "makiotoshi": "巻き落とし", "katasukashi": "肩透かし", "osakate": "大逆手", "sokubiotoshi": "素首落とし",
    "harimanage": "波離間投げ", "ushiromotare": "後ろもたれ", "waridashi": "割り出し", "utchari": "うっちゃり",
    "fumidashi": "踏み出し", "tsutaezori": "伝え反り",
}


def kimarite_jp(name) -> str:
    if not isinstance(name, str) or not name:
        return ""
    return KIMARITE.get(name.strip().lower(), name)
