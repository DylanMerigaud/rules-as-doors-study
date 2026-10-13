import json

import venue_form

REFS = [
    {"citation": 'T. Gloaguen, N. Mundler, M. N. Muller, V. Raychev, and M. Vechev, "A," '
                 'arXiv:2602.11988, 2026.', "arxiv": "2602.11988"},
    {"citation": 'A. Aggarwal and N. Farhady Ghalaty, "B," arXiv:2607.13091, 2026.',
     "arxiv": "2607.13091"},
    {"citation": 'Open Policy Agent, "Philosophy," OPA documentation. Accessed: Sep. 30, 2026. '
                 '[Online]. Available: https://example.org/p', "url": "https://example.org/p"},
    {"citation": 'P. Ralph et al., "Standards," arXiv:2010.03525, 2020.', "arxiv": "2010.03525"},
    {"citation": 'M. Leucker, C. Schallhart, "Brief," J, vol. 78, 2009.',
     "doi": "10.1016/j.jlap.2008.08.004"},
]


def test_author_keys_and_years():
    ks = venue_form.keys(REFS)
    assert [(k["author"], k["label"]) for k in ks] == [
        ("Gloaguen et al.", "2026"), ("Aggarwal and Farhady Ghalaty", "2026"),
        ("Open Policy Agent", "2026"), ("Ralph et al.", "2020"), ("Leucker and Schallhart", "2009")]


def test_groups_narrative_and_reference_list():
    src = ("# T\n\n## Introduction\n\nFiles help little [1], [2]. Aggarwal and Farhady Ghalaty "
           "[2] report rules. Policy as code [3]; standards [4]; monitors [5].\n\n"
           "<!-- a note [9] -->\n\n## References\n\n[1] a\n")
    out, errors = venue_form.form(src, REFS)
    assert errors == []
    assert "help little (Gloaguen et al. 2026; Aggarwal and Farhady Ghalaty 2026)." in out
    assert "Aggarwal and Farhady Ghalaty (2026) report rules." in out
    assert "<!-- a note [9] -->" in out
    refs = out.split("## References\n\n")[1].strip().split("\n\n")
    assert [r.split(",")[0].split('"')[0].strip() for r in refs] == [
        "A. Aggarwal and N. Farhady Ghalaty", "T. Gloaguen", "M. Leucker", "Open Policy Agent",
        "P. Ralph et al."]
    assert refs[0].endswith("https://doi.org/10.48550/arXiv.2607.13091")
    assert refs[2].endswith("https://doi.org/10.1016/j.jlap.2008.08.004")
    assert refs[3].endswith("Available: https://example.org/p")


def test_same_author_and_year_get_letters():
    refs = [{"citation": 'W. Chat et al., "One," X, 2025.', "arxiv": "1"},
            {"citation": 'W. Chat et al., "Two," X, 2025.', "arxiv": "2"}]
    out, errors = venue_form.form("## A\n\nSee [1] and [2].\n\n## References\n", refs)
    assert errors == []
    assert "(Chat et al. 2025a) and (Chat et al. 2025b)" in out
    assert '"One," X, 2025a. https://doi.org/10.48550/arXiv.1' in out


def test_headings_are_numbered_except_front_and_back_matter():
    src = ("# Title\n\n## Abstract\n\nx [1]\n\n## Keywords\n\n- a\n\n## Introduction\n\n"
           "## Method\n\n### Design\n\n### Use of AI tools\n\nSee Section 2.2.\n\n"
           "## Statements and Declarations\n\n### Funding\n\n## Acknowledgments\n\n"
           "## References\n")
    out, errors = venue_form.form(src, REFS[:1])
    assert errors == []
    for h in ("## Abstract", "## Keywords", "## 1 Introduction", "## 2 Method",
              "### 2.1 Design", "### 2.2 Use of AI tools", "## Statements and Declarations",
              "### Funding", "## Acknowledgments", "## References"):
        assert "\n" + h + "\n" in out, h


def test_errors_write_nothing(tmp_path, capsys):
    src = tmp_path / "s.md"
    src.write_text("## Intro\n\nSee [1] and [7]; Section 9.\n\n## References\n",
                   encoding="utf-8")
    refs = tmp_path / "r.jsonl"
    refs.write_text("\n".join(json.dumps(r) for r in REFS[:2]) + "\n", encoding="utf-8")
    out = tmp_path / "o.md"
    assert venue_form.main(["venue_form.py", str(src), str(refs), str(out)]) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "citation [7] names no entry" in err
    assert "reference [2]" in err and "never cited" in err
    assert "Section 9 is referenced" in err


def test_a_heading_already_numbered_is_refused():
    _out, errors = venue_form.form("## 1 Intro\n\nx [1]\n\n## References\n", REFS[:1])
    assert any("already numbered" in e for e in errors)
