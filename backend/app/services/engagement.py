def compute_engagement(
    views,
    likes,
    comments,
    followers=0
):

    interactions = likes + comments

    if views > 0:

        return round(
            interactions / views * 100,
            4
        )

    if followers > 0:

        return round(
            interactions / followers * 100,
            4
        )

    return 0.0