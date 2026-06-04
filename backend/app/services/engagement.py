def compute_engagement(
    views=0,
    likes=0,
    comments=0,
    followers=0
):
    interactions = likes + comments

    # Preferred formula
    if views and views > 0:
        return round((interactions / views) * 100, 4)

    # Fallback for Instagram when views are unavailable
    if followers and followers > 0:
        return round((interactions / followers) * 100, 4)

    # Nothing to divide by
    return 0.0