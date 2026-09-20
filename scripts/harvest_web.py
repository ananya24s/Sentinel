"""Harvest real public web pages as a realistic corpus of *clean* tool output.

Pages are flattened exactly the way the demo's URL mode does it (comments, hidden text and alt text kept).
The corpus is split by site (Wikipedia by page) so evaluation pages come from sites never seen in training.
"""
import concurrent.futures as cf
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sentinel.webfetch import FetchError, fetch_text  # noqa: E402

OUT = ROOT / "data/raw/webcorpus.json"

WIKI = """Bus_rapid_transit Sourdough Photosynthesis Roman_Empire Machine_learning Coffee Jazz Volcano Marathon Chess
Solar_energy Bicycle Tea Great_Barrier_Reef Antarctica Printing_press Vaccine Electric_car Rainforest Olympic_Games
Honey_bee Pizza Mount_Everest Renaissance Internet Cheese Football Monsoon Glacier Origami Chocolate Lighthouse Bridge
Railway Tornado Piano Yoga Silk_Road Coral_reef Compost Cryptography Podcast Skateboarding Solar_eclipse Tide Wine
Basketball Opera Meteorology Aqueduct Sushi Public_library Wind_power Tiramisu Maple_syrup Vaccination Hurricane Tulip""".split()

DOCS = """https://docs.python.org/3/tutorial/introduction.html
https://docs.python.org/3/tutorial/controlflow.html
https://docs.python.org/3/tutorial/datastructures.html
https://docs.python.org/3/tutorial/modules.html
https://docs.python.org/3/tutorial/errors.html
https://docs.python.org/3/tutorial/classes.html
https://docs.python.org/3/library/json.html
https://docs.python.org/3/library/os.path.html
https://developer.mozilla.org/en-US/docs/Web/HTML
https://developer.mozilla.org/en-US/docs/Web/CSS
https://developer.mozilla.org/en-US/docs/Web/JavaScript
https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web
https://doc.rust-lang.org/book/ch01-01-installation.html
https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html
https://git-scm.com/docs/git-commit
https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F
https://www.postgresql.org/docs/current/tutorial-start.html
https://docs.djangoproject.com/en/5.0/intro/tutorial01/
https://flask.palletsprojects.com/en/latest/quickstart/
https://numpy.org/doc/stable/user/absolute_beginners.html
https://pandas.pydata.org/docs/getting_started/intro_tutorials/01_table_oriented.html
https://kubernetes.io/docs/concepts/overview/
https://www.rust-lang.org/learn
https://go.dev/doc/effective_go
https://nodejs.org/en/learn/getting-started/introduction-to-nodejs
https://react.dev/learn
https://vuejs.org/guide/introduction.html
https://www.typescriptlang.org/docs/handbook/2/basic-types.html
https://docs.docker.com/get-started/
https://cloudflare.com/learning/ai/what-is-prompt-injection/""".split()

NEWS = """https://www.bbc.com/news
https://www.bbc.com/news/technology
https://www.bbc.com/sport
https://text.npr.org/
https://lite.cnn.com/
https://apnews.com/
https://www.aljazeera.com/
https://www.theguardian.com/international
https://www.theguardian.com/science
https://news.ycombinator.com/
https://www.reuters.com/
https://www.wired.com/
https://arstechnica.com/
https://www.nature.com/news
https://www.sciencedaily.com/
https://www.nasa.gov/
https://www.nih.gov/news-events
https://www.cdc.gov/
https://www.usa.gov/
https://www.who.int/news
https://www.un.org/en/
https://www.economist.com/
https://www.smithsonianmag.com/
https://www.nationalgeographic.com/
https://www.independent.co.uk/""".split()

BLOGS = """http://www.paulgraham.com/greatwork.html
http://www.paulgraham.com/startupideas.html
http://www.paulgraham.com/love.html
http://www.paulgraham.com/articles.html
https://jvns.ca/blog/
https://overreacted.io/
https://www.joelonsoftware.com/2000/08/09/the-joel-test-12-steps-to-better-code/
https://martinfowler.com/articles/microservices.html
https://blog.codinghorror.com/
https://www.gutenberg.org/
https://www.gutenberg.org/ebooks/1342
https://en.wikibooks.org/wiki/Cookbook:Pancake
https://en.wikibooks.org/wiki/Cookbook:Bread
https://www.simplyrecipes.com/
https://www.bbcgoodfood.com/recipes/collection/easy-recipes
https://www.seriouseats.com/
https://www.epicurious.com/
https://www.thekitchn.com/
https://www.lonelyplanet.com/
https://www.ted.com/talks
https://www.khanacademy.org/
https://www.wikihow.com/Main-Page
https://www.instructables.com/
https://www.python.org/
https://example.com/
https://www.mit.edu/
https://www.stanford.edu/
https://www.ox.ac.uk/
https://www.w3.org/standards/
https://www.eff.org/""".split()

README = """https://raw.githubusercontent.com/psf/requests/main/README.md
https://raw.githubusercontent.com/pallets/flask/main/README.md
https://raw.githubusercontent.com/django/django/main/README.rst
https://raw.githubusercontent.com/numpy/numpy/main/README.md
https://raw.githubusercontent.com/pandas-dev/pandas/main/README.md
https://raw.githubusercontent.com/facebook/react/main/README.md
https://raw.githubusercontent.com/vuejs/core/main/README.md
https://raw.githubusercontent.com/rust-lang/rust/master/README.md
https://raw.githubusercontent.com/golang/go/master/README.md
https://raw.githubusercontent.com/torvalds/linux/master/README
https://raw.githubusercontent.com/microsoft/vscode/main/README.md
https://raw.githubusercontent.com/tensorflow/tensorflow/master/README.md
https://raw.githubusercontent.com/pytorch/pytorch/main/README.md
https://raw.githubusercontent.com/huggingface/transformers/main/README.md
https://raw.githubusercontent.com/nodejs/node/main/README.md
https://raw.githubusercontent.com/kubernetes/kubernetes/master/README.md""".split()


def urls():
    out = [f"https://en.wikipedia.org/wiki/{t}" for t in WIKI]
    out += DOCS + NEWS + BLOGS + README
    return out


def get(u):
    try:
        r = fetch_text(u, timeout=20)
        if len(r["text"]) < 400:
            return None
        return {"url": u, "domain": urlparse(u).hostname, "title": r["title"], "text": r["text"]}
    except FetchError as e:
        return {"url": u, "error": str(e)[:80]}
    except Exception as e:  # noqa: BLE001
        return {"url": u, "error": repr(e)[:80]}


def main():
    us = urls()
    print(len(us), "urls", flush=True)
    ok, bad = [], []
    with cf.ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(get, us)):
            (ok if r and "text" in r else bad).append(r)
            if i % 20 == 0:
                print(f"  {i}/{len(us)}  ok={len(ok)}", flush=True)
    json.dump(ok, open(OUT, "w"))
    print("saved", len(ok), "pages;", len(bad), "failed")
    for b in bad[:12]:
        print("  fail:", (b or {}).get("url"), (b or {}).get("error"))


if __name__ == "__main__":
    main()
