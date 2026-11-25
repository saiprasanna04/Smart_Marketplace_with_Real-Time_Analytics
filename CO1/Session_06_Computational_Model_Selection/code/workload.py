"""Shared deterministic catalogue expansion and query definitions."""


DEFAULT_QUERY = ("Electronics", 100.0, 1)


def generate_scaled_catalogue(
    base_catalogue: list[dict[str, object]], target_size: int
) -> list[dict[str, object]]:
    """Cycle through valid source records to create a reproducible larger workload."""
    if target_size < 0:
        raise ValueError("target_size must be greater than or equal to 0")
    if target_size > 0 and not base_catalogue:
        raise ValueError("Cannot generate products from an empty base catalogue")

    generated: list[dict[str, object]] = []
    used_ids = {str(product["product_id"]) for product in base_catalogue}

    for index in range(target_size):
        source = base_catalogue[index % len(base_catalogue)]
        product = dict(source)
        if index >= len(base_catalogue):
            product_id = f"M1-{index + 1:06d}"
            while product_id in used_ids:
                product_id = f"X-{product_id}"
            product["product_id"] = product_id
            product["title"] = f"{source['title']} (benchmark sample {index + 1})"
        generated.append(product)
        used_ids.add(str(product["product_id"]))

    return generated
