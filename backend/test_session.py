import instaloader

L = instaloader.Instaloader()

L.load_session_from_file("sahil_katkamwar")

post = instaloader.Post.from_shortcode(
    L.context,
    "DYs2sTkgJzN"
)

print(post.owner_username)