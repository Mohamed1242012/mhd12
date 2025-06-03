from flask import Flask, render_template, url_for, request, abort
import markdown
from markdown.extensions.toc import TocExtension
import yaml
from flask import Response
from datetime import datetime
from email.utils import format_datetime

app = Flask(__name__)
app.url_map.strict_slashes = False

@app.before_request
def log_request_info():
    print(f"Received a {request.method} request to {request.path}")

def md_to_html(file_name):
    with open(f"static/posts/md/{file_name}") as md_file:
        md_content = "[TOC]\n\n" + md_file.read()
    html = markdown.markdown(md_content,extensions=[TocExtension(baselevel=3),'abbr','fenced_code','footnotes','tables',])
    return html

def readPosts(posts_to_read,reverse):
    # Example of the output:
    [
        {
            "id": 0,
            "title": "Test Title",
            "img": "https://picsum.photos/200",
            "name": "0.md",
            "date": "10.2.2024",
            "tags": "Linux, Arch, Distro's",
            "pinned": True,
            "html": "html_content",
        },
        ...
    ]
    posts = []
    required_feilds = ["title","img","name","date","tags","pinned","excerpt"]
    post_number = 0
    while True:
        try:
            with open(f"static/posts/metadata/{post_number}.yml") as file:
                metadata = yaml.safe_load(file)
                if not all(field in metadata for field in required_feilds):
                    missing_fields = [field for field in required_feilds if field not in metadata]
                    print(f"Skipping {post_number}.yml, missing fields: {missing_fields}")
                    post_number += 1
                    continue
                metadata["id"] = post_number
                metadata["html"] = md_to_html(metadata["name"])
                # metadata["excerpt"] = metadata["excerpt"]+"..."
                if metadata.get("pinned") == True and metadata.get("priority",None) == None:
                    metadata["priority"] = 5
                posts.append(metadata)
            post_number += 1
        except FileNotFoundError:
            break
    if reverse == True:
        posts.reverse()
    if posts_to_read != 0:
        posts = posts[:posts_to_read]
    return posts

def convert_to_rfc822(date_str):
    # Convert "1.6.2025" to datetime
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    return format_datetime(dt)


@app.route("/rss.xml")
def rss_feed():
    posts = readPosts(0, True)
    rss_items = ""
    for post in posts:
        rss_items += f"""
        <item>
            <title>{post['title']}</title>
            <link>{request.url_root.rstrip('/')}{url_for('blog_page', id=post['id'])}</link>
            <description><![CDATA[{post['excerpt']}]]></description>
            <pubDate>{convert_to_rfc822(post['date'])}</pubDate>
            <guid>{request.url_root.rstrip('/')}{url_for('blog_page', id=post['id'])}</guid>
            <author>mhd12</author>
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
    <channel>
        <title>mhd12 Blog</title>
        <link>{request.url_root.rstrip('/')}</link>
        <description>mhd12 (Mohamed Elsayed) - Blog RSS Feed</description>
        {rss_items}
    </channel>
    </rss>
    """
    return Response(rss, mimetype='application/rss+xml')

@app.route("/")
def home():
    page_info={
        "title": "Home",
        "description": "mhd12 (Mohamed Elsayed) - Web Developer, Homelabber, based in Sharjah, UAE. Explore my projects, blog posts, and more.",
        "img": url_for("static", filename="me.png")
    }
    posts = readPosts(3,True)
    return render_template("home.html",posts=posts, page_info=page_info)

@app.route("/blog")
def blog():
    page_info={
        "title": "Blog",
        "description": "mhd12 (Mohamed Elsayed) - Web Developer, Homelabber, based in Sharjah, UAE. Explore my projects, blog posts, and more.",
        "img": url_for("static", filename="me.png")
    }
    sort = request.args.get("sort", "new")
    if sort == "old":
        posts = readPosts(0, False)
    else:
        posts = readPosts(0, True)
        sort = "new"
    return render_template("blog.html",posts=posts, page_info=page_info, sort=sort)

@app.route("/blog/id/<id>")
def blog_page(id):
    posts = readPosts(0, True)
    post = next((p for p in posts if str(p["id"]) == str(id)), None)
    if post is None:
        abort(404, description="Post not found")
    try:
        page_info = {
            "title": post["title"],
            "description": post["excerpt"],
            "img": url_for("static", filename=f"posts/img/{post['img']}"),
            "keywords": post["tags"]
        }
    except Exception as e:
        abort(500)
    return render_template("blog_page.html",page_info=page_info,post=post)

@app.errorhandler(Exception)
def handle_all_errors(error):
    error_str = str(error)
    if ":" in error_str:
        code_str, message = error_str.split(":", 1)
        try:
            code = int(code_str.strip().split()[0])
        except Exception:
            code = getattr(error, "code", 500)
        message = message.strip()
    else:
        code = getattr(error, "code", 500)
        message = error_str

    # Hide internal details for 500 and similar errors
    if code == 500 or code >= 500:
        message = "An error occurred on our side, sorry for the inconvenience."
    elif code == 403:
        message = "You do not have permission to access this resource."
    # You can add more codes here if needed

    error_info = {
        "code": code,
        "message": message,
    }
    page_info = {
        "title": f"{code} Error",
    }
    return render_template("errors/error.html", page_info=page_info, error=error_info), code