#!/usr/bin/env python3

import json
import re
from datetime import datetime, timezone
from pathlib import Path


QUEUE_FILE = Path(
    "data/content/production-topic-queue.json"
)

PRODUCTS_FILE = Path(
    "data/content/production-products.json"
)

OUTPUT_FILE = Path(
    "data/content/content-plans.json"
)


ACTION_CONFIG = {
    "new_guide": {
        "content_type": "guide",
        "generation_action": "create_page",
    },
    "guide_cluster": {
        "content_type": "supporting_guide",
        "generation_action": "create_cluster_page",
    },
    "product_block": {
        "content_type": "product_block",
        "generation_action": "create_product_block",
    },
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_topic(value):
    return " ".join(
        str(value).strip().lower().split()
    )


def slugify(value):
    value = normalize_topic(value)

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    )

    return value.strip("-")


def build_title(topic):
    return topic.title()


def build_search_intent(action):
    if action == "new_guide":
        return "commercial_investigation"

    if action == "guide_cluster":
        return "commercial_investigation"

    if action == "product_block":
        return "transactional_support"

    return "informational"


def build_outline(topic, action):
    if action == "new_guide":
        return [
            {
                "section_order": 1,
                "section_key": "introduction",
                "heading": f"Best {topic}",
                "purpose": (
                    "Introduce the product category and "
                    "explain who the guide is for."
                ),
            },
            {
                "section_order": 2,
                "section_key": "top_picks",
                "heading": "Our top picks",
                "purpose": (
                    "Summarise the selected products "
                    "before detailed recommendations."
                ),
            },
            {
                "section_order": 3,
                "section_key": "product_recommendations",
                "heading": (
                    f"Best {topic} recommendations"
                ),
                "purpose": (
                    "Present selected affiliate products "
                    "with useful buying context."
                ),
            },
            {
                "section_order": 4,
                "section_key": "buying_guide",
                "heading": "What to look for",
                "purpose": (
                    "Explain practical buying criteria "
                    "for UK drivers."
                ),
            },
            {
                "section_order": 5,
                "section_key": "faq",
                "heading": "Frequently asked questions",
                "purpose": (
                    "Answer common questions related "
                    "to the product category."
                ),
            },
        ]

    if action == "guide_cluster":
        return [
            {
                "section_order": 1,
                "section_key": "introduction",
                "heading": topic.title(),
                "purpose": (
                    "Introduce the topic and connect it "
                    "to the parent guide cluster."
                ),
            },
            {
                "section_order": 2,
                "section_key": "use_cases",
                "heading": "Who this product is for",
                "purpose": (
                    "Explain driver needs and practical "
                    "use cases."
                ),
            },
            {
                "section_order": 3,
                "section_key": "product_recommendations",
                "heading": "Recommended products",
                "purpose": (
                    "Present selected affiliate products "
                    "with comparison context."
                ),
            },
            {
                "section_order": 4,
                "section_key": "buying_advice",
                "heading": "Buying advice",
                "purpose": (
                    "Explain the most important product "
                    "selection criteria."
                ),
            },
            {
                "section_order": 5,
                "section_key": "cluster_link",
                "heading": "More driver comfort guides",
                "purpose": (
                    "Link the page to its parent content "
                    "cluster and related guides."
                ),
            },
        ]

    if action == "product_block":
        return [
            {
                "section_order": 1,
                "section_key": "product_block_intro",
                "heading": f"Recommended {topic}",
                "purpose": (
                    "Introduce the recommendation block "
                    "inside the target guide."
                ),
            },
            {
                "section_order": 2,
                "section_key": "product_recommendations",
                "heading": "Top product picks",
                "purpose": (
                    "Render selected affiliate products "
                    "with concise recommendation copy."
                ),
            },
        ]

    return []


def build_product_slots(products):
    slots = []

    for index, product in enumerate(products, 1):
        slots.append({
            "slot": index,
            "product_id": product["product_id"],
            "product_title": product["product_title"],
            "product_main_image_url":
                product["product_main_image_url"],
            "promotion_link":
                product["promotion_link"],
            "target_sale_price":
                product["target_sale_price"],
            "currency":
                product["currency"],
            "sales_volume":
                product["sales_volume"],
            "evaluate_rate":
                product["evaluate_rate"],
            "commission_rate":
                product["commission_rate"],
            "estimated_commission_value":
                product.get(
                    "estimated_commission_value"
                ),
            "product_score":
                product["selection_score"],
            "selection_reason":
                product["selection_reason"],
        })

    return slots


def main():
    queue_data = json.loads(
        QUEUE_FILE.read_text(encoding="utf-8")
    )

    product_data = json.loads(
        PRODUCTS_FILE.read_text(encoding="utf-8")
    )

    queue_topics = queue_data["topics"]
    product_topics = product_data["topics"]

    products_by_topic = {
        item["normalized_topic"]: item
        for item in product_topics
    }

    plans = []
    missing_product_topics = []

    for queue_item in queue_topics:
        topic = queue_item["topic"]
        normalized_topic = queue_item[
            "normalized_topic"
        ]

        product_topic = products_by_topic.get(
            normalized_topic
        )

        if product_topic is None:
            missing_product_topics.append(
                normalized_topic
            )
            continue

        action = queue_item["production_action"]

        if action not in ACTION_CONFIG:
            raise ValueError(
                f"Unsupported production action: {action}"
            )

        products = product_topic["products"]

        plan = {
            "content_priority":
                queue_item["production_priority"],
            "topic": topic,
            "normalized_topic": normalized_topic,
            "slug": slugify(topic),
            "working_title": build_title(topic),
            "production_action": action,
            "content_type":
                ACTION_CONFIG[action]["content_type"],
            "generation_action":
                ACTION_CONFIG[action][
                    "generation_action"
                ],
            "search_intent":
                build_search_intent(action),
            "final_opportunity_score":
                queue_item["final_opportunity_score"],
            "opportunity_status":
                queue_item["source_final_status"],
            "strategy":
                queue_item["strategy_source"],
            "target": (
                queue_item.get("cluster")
                if action == "guide_cluster"
                else queue_item.get("target")
                if action == "product_block"
                else None
            ),
            "outline":
                build_outline(topic, action),
            "product_count": len(products),
            "product_slots":
                build_product_slots(products),
            "content_status": "planned",
            "approval_status": "pending",
            "generation_status": "not_started",
            "publish_status": "not_published",
        }

        plans.append(plan)

    plans.sort(
        key=lambda item: item["content_priority"]
    )

    for index, plan in enumerate(plans, 1):
        plan["plan_priority"] = index

    action_counts = {}

    for plan in plans:
        action = plan["production_action"]

        action_counts[action] = (
            action_counts.get(action, 0) + 1
        )

    output = {
        "source": "driverz_content_planning",
        "planner_version": 1,
        "generated_at": utc_now(),
        "source_queue_version":
            queue_data["queue_version"],
        "source_product_selector_version":
            product_data["selector_version"],
        "input_queue_topic_count":
            len(queue_topics),
        "input_product_topic_count":
            len(product_topics),
        "content_plan_count":
            len(plans),
        "missing_product_topic_count":
            len(missing_product_topics),
        "missing_product_topics":
            missing_product_topics,
        "action_counts":
            action_counts,
        "planning_policy": {
            "requires_selected_products": True,
            "default_content_status": "planned",
            "default_approval_status": "pending",
            "default_generation_status":
                "not_started",
            "default_publish_status":
                "not_published",
            "automatic_generation": False,
            "automatic_publishing": False,
        },
        "plans": plans,
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

    print(
        "===== Driverz Content Planner v1 ====="
    )
    print("Queue topics:", len(queue_topics))
    print("Product topics:", len(product_topics))
    print("Content plans:", len(plans))
    print(
        "Missing product topics:",
        len(missing_product_topics),
    )
    print("Action counts:", action_counts)
    print("Saved:", OUTPUT_FILE)

    print("\n===== CONTENT PLANS =====")

    for plan in plans:
        print(
            plan["plan_priority"],
            "| score=",
            plan["final_opportunity_score"],
            "| action=",
            plan["production_action"],
            "| type=",
            plan["content_type"],
            "| products=",
            plan["product_count"],
            "| target=",
            plan["target"] or "-",
            "|",
            plan["topic"],
        )


if __name__ == "__main__":
    main()
