#!/usr/bin/env python3

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path("data/affiliate/raw/aliexpress_products.json")
OUTPUT_FILE = Path(
    "data/affiliate/candidates/aliexpress_products.json"
)

MIN_RATING = 90.0
MIN_RELEVANCE = 70.0
TOP_N_PER_KEYWORD = 20


STOPWORDS = {
    "a", "an", "and", "auto", "automotive", "for",
    "in", "of", "the", "to", "universal", "with",
}


NEGATIVE_TERMS = {
    "car phone holder": [
        "metal plate",
        "iron sheet",
        "replacement plate",
        "adhesive plate",
        "finger ring",
        "sticker",
    ],
    "car boot organiser": [
        "hook",
        "clip",
        "strap only",
        "replacement",
        "net only",
    ],
    "car seat organiser": [
        "hook",
        "clip",
        "seat cover",
        "replacement",
        "strap only",
    ],
    "car sun shade": [
        "sticker",
        "decal",
        "toy",
        "replacement part",
    ],
    "car cleaning brush": [
        "makeup brush",
        "toothbrush",
        "paint brush",
        "nail brush",
        "replacement head",
    ],
}


def parse_percent(value):
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return 0.0


def parse_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def parse_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def tokenize(text):
    return set(
        re.findall(r"[a-z0-9]+", str(text).lower())
    )


def keyword_relevance_score(title, keyword):
    title_lower = str(title).lower()
    title_tokens = tokenize(title)

    keyword_tokens = [
        token
        for token in tokenize(keyword)
        if token not in STOPWORDS
    ]

    if not keyword_tokens:
        return 0.0

    matched_tokens = sum(
        token in title_tokens
        for token in keyword_tokens
    )

    coverage = matched_tokens / len(keyword_tokens)

    score = coverage * 70.0

    if keyword.lower() in title_lower:
        score += 20.0

    if coverage == 1.0:
        score += 10.0

    for negative_term in NEGATIVE_TERMS.get(keyword, []):
        if negative_term in title_lower:
            score -= 35.0

    return max(0.0, min(score, 100.0))


def sales_score(volume):
    volume = max(parse_int(volume), 0)

    return min(
        math.log10(volume + 1) / 5.0 * 100.0,
        100.0,
    )


def rating_score(rating):
    return max(
        0.0,
        min((rating - 90.0) * 10.0, 100.0),
    )


def commission_score(rate):
    return max(
        0.0,
        min(rate / 10.0 * 100.0, 100.0),
    )


def price_score(price):
    price = parse_float(price)

    if 5 <= price <= 30:
        return 100.0

    if 2 <= price < 5:
        return 70.0

    if 30 < price <= 50:
        return 60.0

    return 30.0


def estimated_commission_value(product):
    price = parse_float(product.get("target_sale_price"))
    commission = parse_percent(product.get("commission_rate"))

    return price * commission / 100.0


def score_product_for_keyword(product, keyword):
    rating = parse_percent(product.get("evaluate_rate"))
    commission = parse_percent(product.get("commission_rate"))

    relevance = keyword_relevance_score(
        product.get("product_title", ""),
        keyword,
    )

    sales = sales_score(product.get("sales_volume"))
    rating_component = rating_score(rating)
    commission_component = commission_score(commission)
    price_component = price_score(
        product.get("target_sale_price")
    )

    total = (
        relevance * 0.40
        + sales * 0.20
        + rating_component * 0.20
        + commission_component * 0.15
        + price_component * 0.05
    )

    return {
        "score": round(total, 2),
        "relevance": round(relevance, 2),
        "sales": round(sales, 2),
        "rating": round(rating_component, 2),
        "commission": round(commission_component, 2),
        "price": round(price_component, 2),
    }


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    products = data["products"]

    keyword_order = [
        stat["keyword"]
        for stat in data["collection_stats"]
    ]

    rankings_by_keyword = {}

    rejected_low_rating = 0
    rejected_missing_promotion_link = 0
    rejected_low_relevance_slots = 0

    rating_eligible_products = []

    for product in products:
        rating = parse_percent(product.get("evaluate_rate"))

        if rating < MIN_RATING:
            rejected_low_rating += 1
            continue

        if not product.get("promotion_link"):
            rejected_missing_promotion_link += 1
            continue

        rating_eligible_products.append(product)

    for keyword in keyword_order:
        ranked = []

        for product in rating_eligible_products:
            if keyword not in product.get("matched_keywords", []):
                continue

            breakdown = score_product_for_keyword(
                product,
                keyword,
            )

            if breakdown["relevance"] < MIN_RELEVANCE:
                rejected_low_relevance_slots += 1
                continue

            candidate = dict(product)

            candidate["ranking_keyword"] = keyword
            candidate["score"] = breakdown["score"]
            candidate["estimated_commission_value"] = round(
                estimated_commission_value(product),
                4,
            )
            candidate["score_breakdown"] = breakdown

            ranked.append(candidate)

        ranked.sort(
            key=lambda product: (
                product["score"],
                product["estimated_commission_value"],
                parse_int(product.get("sales_volume")),
            ),
            reverse=True,
        )

        rankings_by_keyword[keyword] = ranked[
            :TOP_N_PER_KEYWORD
        ]

    global_pool = {}

    for keyword in keyword_order:
        for product in rankings_by_keyword[keyword]:
            product_id = product["product_id"]

            if product_id not in global_pool:
                global_product = dict(product)

                global_product["selected_for_keywords"] = [
                    keyword
                ]

                global_product[
                    "best_ranking_keyword"
                ] = keyword

                global_pool[product_id] = global_product

            else:
                existing = global_pool[product_id]

                if keyword not in existing[
                    "selected_for_keywords"
                ]:
                    existing[
                        "selected_for_keywords"
                    ].append(keyword)

                if product["score"] > existing["score"]:
                    selected_keywords = existing[
                        "selected_for_keywords"
                    ]

                    replacement = dict(product)

                    replacement[
                        "selected_for_keywords"
                    ] = selected_keywords

                    replacement[
                        "best_ranking_keyword"
                    ] = keyword

                    global_pool[product_id] = replacement

    global_candidates = list(global_pool.values())

    global_candidates.sort(
        key=lambda product: (
            product["score"],
            product["estimated_commission_value"],
            parse_int(product.get("sales_volume")),
        ),
        reverse=True,
    )

    ranking_summary = {}

    for keyword in keyword_order:
        ranking_summary[keyword] = {
            "selected_count": len(
                rankings_by_keyword[keyword]
            ),
            "top_score": (
                rankings_by_keyword[keyword][0]["score"]
                if rankings_by_keyword[keyword]
                else None
            ),
        }

    output = {
        "source": "driverz_aliexpress_scoring",
        "scorer_version": 3,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_generated_at": data["generated_at"],
        "market": data["market"],
        "collection": data["collection"],
        "quality_gate": {
            "min_rating": MIN_RATING,
            "min_relevance": MIN_RELEVANCE,
            "requires_promotion_link": True,
            "top_n_per_keyword": TOP_N_PER_KEYWORD,
        },
        "input_unique_product_count": len(products),
        "rejected_low_rating_count": rejected_low_rating,
        "rejected_missing_promotion_link_count":
            rejected_missing_promotion_link,
        "rejected_low_relevance_slots":
            rejected_low_relevance_slots,
        "global_candidate_count": len(global_candidates),
        "ranking_summary": ranking_summary,
        "rankings_by_keyword": rankings_by_keyword,
        "products": global_candidates,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")

    temp_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temp_file.replace(OUTPUT_FILE)

    print("===== Driverz AliExpress Scorer v3 =====")
    print("Input products:", len(products))
    print("Rejected low rating:", rejected_low_rating)
    print(
        "Rejected missing promotion link:",
        rejected_missing_promotion_link,
    )
    print(
        "Rejected low relevance slots:",
        rejected_low_relevance_slots,
    )
    print(
        "Global unique candidates:",
        len(global_candidates),
    )

    print("\n===== PER-KEYWORD RANKING =====")

    for keyword in keyword_order:
        ranked = rankings_by_keyword[keyword]

        print(
            keyword,
            "| selected=",
            len(ranked),
            "| top_score=",
            ranked[0]["score"] if ranked else "NONE",
        )

    print("\n===== GLOBAL TOP 15 =====")

    for index, product in enumerate(
        global_candidates[:15], 1
    ):
        print(
            index,
            "| score=" + str(product["score"]),
            "| relevance="
            + str(product["score_breakdown"]["relevance"]),
            "| est_commission=£"
            + str(product["estimated_commission_value"]),
            "| best="
            + product["best_ranking_keyword"],
            "|",
            product["product_title"][:75],
        )


if __name__ == "__main__":
    main()
