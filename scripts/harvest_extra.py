"""Harvest ~100 extra real pages (AI / security / technical docs / AI news) for TRAINING only.

Why: the first corpus had little technical documentation, so the scorer learned to treat words like "prompt",
"credentials" or "AI model" as attack cues and raised false alarms on docs pages. These pages are always assigned to
the training split (new domains only), so the held-out test sites are untouched.
"""
import concurrent.futures as cf
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from harvest_web import get  # noqa: E402

WIKI = """Prompt_engineering Large_language_model Artificial_intelligence Chatbot Natural_language_processing Password Phishing
Computer_security Command-line_interface Shell_script Python_(programming_language) Read–eval–print_loop Social_engineering_(security)
Multi-factor_authentication Malware Ransomware Encryption Firewall_(computing) SQL_injection Cross-site_scripting Operating_system
Linux_kernel Unix_shell Bash_(Unix_shell) Git HTML JavaScript Application_programming_interface Web_browser Search_engine Email
Spam_(email) Cloud_computing Artificial_neural_network Transformer_(deep_learning_architecture) ChatGPT Turing_test Robot Data_breach
Privacy OAuth HTTP_cookie Cybersecurity_engineering Authentication Access_control Biometrics Virtual_assistant Speech_recognition
Computer_vision Reinforcement_learning Software_engineering Debugging Compiler Database Computer_network Domain_Name_System""".split()

OTHER = """https://pip.pypa.io/en/stable/user_guide/
https://docs.pytest.org/en/stable/getting-started.html
https://click.palletsprojects.com/en/latest/quickstart/
https://requests.readthedocs.io/en/latest/user/quickstart/
https://fastapi.tiangolo.com/tutorial/first-steps/
https://docs.sqlalchemy.org/en/20/tutorial/index.html
https://huggingface.co/docs/transformers/llm_tutorial
https://huggingface.co/docs/transformers/chat_templating
https://huggingface.co/docs/transformers/quicktour
https://scikit-learn.org/stable/getting_started.html
https://matplotlib.org/stable/users/getting_started/
https://jupyter-notebook.readthedocs.io/en/stable/notebook.html
https://www.w3schools.com/python/python_intro.asp
https://www.geeksforgeeks.org/python-programming-language-tutorial/
https://realpython.com/python-repl/
https://learn.microsoft.com/en-us/powershell/scripting/overview
https://www.gnu.org/software/bash/manual/bash.html
https://man7.org/linux/man-pages/man1/ls.1.html
https://docs.github.com/en/get-started/start-your-journey/about-github-and-git
https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
https://owasp.org/www-community/attacks/xss/
https://owasp.org/www-project-top-ten/
https://www.cisa.gov/topics/cybersecurity-best-practices
https://www.ncsc.gov.uk/collection/top-tips-for-staying-secure-online
https://www.ftc.gov/business-guidance/small-businesses/cybersecurity
https://www.theverge.com/ai-artificial-intelligence
https://techcrunch.com/category/artificial-intelligence/
https://www.technologyreview.com/topic/artificial-intelligence/
https://www.wired.com/tag/artificial-intelligence/
https://www.theguardian.com/technology/artificialintelligenceai
https://blog.google/technology/ai/
https://www.nature.com/subjects/machine-learning
https://www.sciencedaily.com/news/computers_math/artificial_intelligence/
https://www.zdnet.com/topic/artificial-intelligence/
https://venturebeat.com/ai/
https://www.infoworld.com/artificial-intelligence/
https://www.freecodecamp.org/news/tag/python/
https://dev.to/t/python
https://www.tutorialspoint.com/python/index.htm
https://wiki.python.org/moin/BeginnersGuide
https://peps.python.org/pep-0008/
https://www.postgresql.org/docs/current/sql-select.html
https://redis.io/docs/latest/develop/get-started/
https://docs.docker.com/engine/reference/commandline/run/
https://kubernetes.io/docs/tasks/tools/
https://www.terraform.io/intro
https://git-scm.com/docs/git-push
https://curl.se/docs/manual.html
https://nginx.org/en/docs/beginners_guide.html
https://httpd.apache.org/docs/2.4/getting-started.html
https://www.sqlite.org/quickstart.html""".split()


def main():
    urls = [f"https://en.wikipedia.org/wiki/{t}" for t in WIKI] + OTHER
    print(len(urls), "urls", flush=True)
    ok, bad = [], []
    with cf.ThreadPoolExecutor(8) as ex:
        for r in ex.map(get, urls):
            (ok if r and "text" in r else bad).append(r)
    json.dump(ok, open(ROOT / "data/raw/webcorpus_extra.json", "w"))
    print("saved", len(ok), "pages;", len(bad), "failed")


if __name__ == "__main__":
    main()
