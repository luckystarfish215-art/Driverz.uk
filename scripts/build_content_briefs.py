#!/usr/bin/env python3

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path(
    "data/content/content-plans.json"
)

OUTPUT_FILE = Path(
    "data/content/content-briefs.json"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return str(value).strip().lower()


def slugify(value):
    value = normalize(value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def title_case_topic(topic):
    return " ".join(
        word.upper() if word == "ev" else word.capitalize()
        for word in normalize(topic).split()
    )


def build_search_intent(plan):
    action = plan["production_action"]

    if action == "new_guide":
        return "commercial_investigation"

    if action == "guide_cluster":
        return "commercial_investigation_supporting"

    if action == "product_block":
        return "transactional_supporting"

    raise ValueError(
        "Unsupported production action: " + action
    )


def build_page_title_direction(plan):
    topic_title = title_case_topic(plan["topic"])

    if plan["production_action"] == "new_guide":
        return (
            "Best "
            + topic_title
            + " for UK Drivers: Buying Guide"
        )

    if plan["production_action"] == "guide_cluster":
        return (
            topic_title
            + ": What UK Drivers Should Know Before Buying"
        )

    if plan["production_action"] == "product_block":
        return (
            "Recommended "
            + topic_title
            + " for UK Drivers"
        )

    raise ValueError(
        "Unsupported production action"
    )


def build_primary_keyword(plan):
    return normalize(plan["topic"])


def build_secondary_keywords(plan):
    topic = normalize(plan["topic"])
    topic_title = title_case_topic(topic)

    keywords = [
        "best " + topic + " uk",
        topic + " for uk drivers",
        topic + " buying guide",
        topic + " reviews",
        topic_title.lower() + " recommendations",
    ]

    return list(dict.fromkeys(keywords))


def build_audience(plan):
    action = plan["production_action"]

    if action == "new_guide":
        return [
            "UK drivers researching products before purchase",
            "Drivers comparing practical car accessories",
            "Readers looking for product recommendations",
        ]

    if action == "guide_cluster":
        return [
            "UK drivers researching a specific accessory type",
            "Readers comparing comfort and convenience products",
            "Visitors entering from a broader guide cluster",
        ]

    if action == "product_block":
        return [
            "Readers already viewing a related Driverz guide",
            "Visitors looking for practical product recommendations",
            "Users with stronger purchase intent",
        ]

    raise ValueError(
        "Unsupported production action"
    )


def build_content_objective(plan):
    topic = normalize(plan["topic"])
    action = plan["production_action"]

    if action == "new_guide":
        return (
            "Create a useful UK-focused buying guide for "
            + topic
            + ", explain key buying considerations, compare selected "
            "products, and help readers make an informed choice."
        )

    if action == "guide_cluster":
        return (
            "Create a focused supporting guide for "
            + topic
            + " that adds topical depth to the parent content cluster, "
            "answers specific buying questions, and presents selected "
            "products where commercially relevant."
        )

    if action == "product_block":
        return (
            "Create a reusable recommendation block for "
            + topic
            + " that can be inserted into the configured target guide "
            "without requiring a standalone article."
        )

    raise ValueError(
        "Unsupported production action"
    )


def build_required_sections(plan):
    topic_title = title_case_topic(plan["topic"])
    action = plan["production_action"]

    if action == "new_guide":
        return [
            "Introduction and who this guide is for",
            "Quick recommendations",
            "How we selected the products",
            "What to consider when buying " + topic_title,
            "Product comparison",
            "Individual product recommendations",
            "Frequently asked questions",
            "Final recommendation",
            "Affiliate disclosure",
        ]

    if action == "guide_cluster":
        return [
            "Introduction",
            "Who should consider " + topic_title,
            "Key buying considerations",
            "Product comparison",
            "Selected product recommendations",
            "Common questions",
            "How this topic relates to the parent guide cluster",
            "Final recommendation",
            "Affiliate disclosure",
        ]

    if action == "product_block":
        return [
            "Short contextual introduction",
            "Recommended products",
            "Why these products were selected",
            "Buying considerations",
            "Affiliate disclosure",
        ]

    raise ValueError(
        "Unsupported production action"
    )


def build_internal_linking(plan):
    action = plan["production_action"]

    result = {
        "link_to_driverz_tools": True,
        "link_to_relevant_guides": True,
        "avoid_orphan_content": True,
    }

    if action == "guide_cluster":
        result["parent_cluster"] = plan["target"]

    elif action == "product_block":
        result["insertion_target"] = plan["target"]

    return result


def build_product_summary(product):
    required_fields = {
        "slot",
        "product_id",
        "product_title",
        "product_main_image_url",
        "promotion_link",
        "target_sale_price",
        "currency",
        "sales_volume",
        "evaluate_rate",
        "commission_rate",
        "estimated_commission_value",
        "product_score",
        "selection_reason",
    }

    missing_fields = sorted(
        required_fields - set(product.keys())
    )

    if missing_fields:
        raise ValueError(
            "Missing product fields: "
            + ", ".join(missing_fields)
        )

    return {
        "slot": product["slot"],
        "product_id": product["product_id"],
        "product_title": product["product_title"],
        "product_main_image_url":
            product["product_main_image_url"],
        "promotion_link": product["promotion_link"],
        "target_sale_price":
            product["target_sale_price"],
        "currency": product["currency"],
        "sales_volume": product["sales_volume"],
        "evaluate_rate": product["evaluate_rate"],
        "commission_rate":
            product["commission_rate"],
        "estimated_commission_value":
            product["estimated_commission_value"],
        "product_score": product["product_score"],
        "selection_reason":
            product["selection_reason"],
    }

def build_workflow_guardrails(plan):
    return {
        "brief_status": "draft",
        "requires_human_review": True,
        "automatic_generation_enabled": False,
        "automatic_publishing_enabled": False,
        "product_links_require_validation": True,
        "claims_require_source_validation": True,
        "pricing_requires_freshness_check": True,
        "editorial_notes": [
            (
                "Do not publish product prices as permanent facts; "
                "prices and availability can change."
            ),
            (
                "Do not make unsupported safety, legal, medical, "
                "performance, or compatibility claims."
            ),
            (
                "Review product relevance and promotion links "
                "before content approval."
            ),
        ],
    }


def build_brief(plan):
    products = plan["product_slots"]

    if len(products) != 5:
        raise ValueError(
            "Expected 5 product slots for "
            + plan["topic"]
            + ", got "
            + str(len(products))
        )

    if not products:
        raise ValueError(
            "No products available for "
            + plan["topic"]
        )

    return {
        "topic": plan["topic"],
        "normalized_topic": plan["normalized_topic"],
        "source_content_priority":
            plan["content_priority"],
        "final_opportunity_score":
            plan["final_opportunity_score"],
        "production_action":
            plan["production_action"],
        "content_type":
            plan["content_type"],
        "routing_target":
            plan["target"],
        "brief_title":
            build_page_title_direction(plan),
        "primary_keyword":
            build_primary_keyword(plan),
        "secondary_keywords":
            build_secondary_keywords(plan),
        "target_audience":
            build_audience(plan),
        "content_objective":
            build_content_objective(plan),
        "required_sections":
            build_required_sections(plan),
        "internal_linking":
            build_internal_linking(plan),
        "selected_product_count":
            len(products),
        "products": [
            build_product_summary(product)
            for product in products
        ],
        "workflow":
            build_workflow_guardrails(plan),
    }


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    plans = data["plans"]

    briefs = [
        build_brief(plan)
        for plan in plans
    ]

    briefs.sort(
        key=lambda item: (
            item["source_content_priority"],
            -item["final_opportunity_score"],
        )
    )

    for index, brief in enumerate(briefs, 1):
        brief["brief_priority"] = index

    action_counts = Counter(
        brief["production_action"]
        for brief in briefs
    )

    content_type_counts = Counter(
        brief["content_type"]
        for brief in briefs
    )

    output = {
        "source": "driverz_content_briefs",
        "brief_builder_version": 1,
        "generated_at": utc_now(),
        "source_planner_version":
            data["planner_version"],
        "input_plan_count": len(plans),
        "brief_count": len(briefs),
        "action_counts": dict(action_counts),
        "content_type_counts":
            dict(content_type_counts),
        "workflow_policy": {
            "human_review_required": True,
            "automatic_generation_enabled": False,
            "automatic_publishing_enabled": False,
        },
        "briefs": briefs,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(
        ".json.tmp"
    )

    temp_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temp_file.replace(OUTPUT_FILE)

    print("===== Driverz Content Brief Builder v1 =====")
    print("Input plans:", len(plans))
    print("Content briefs:", len(briefs))
    print("Action counts:", dict(action_counts))
    print(
        "Content type counts:",
        dict(content_type_counts),
    )
    print("Saved:", OUTPUT_FILE)

    print("\n===== CONTENT BRIEFS =====")

    for brief in briefs:
        print(
            brief["brief_priority"],
            "| score=",
            brief["final_opportunity_score"],
            "| action=",
            brief["production_action"],
            "| type=",
            brief["content_type"],
            "| products=",
            brief["selected_product_count"],
            "| target=",
            brief["routing_target"] or "-",
            "|",
            brief["topic"],
        )


if __name__ == "__main__":
    main()
