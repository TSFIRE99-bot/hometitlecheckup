from web.content import parse


def test_sections_icons_lists_and_notes():
    page = parse("""<!-- a note -->
# My page
Hello **there**.

## First {heart}
One paragraph
that wraps.

- a bullet
  that continues
- another

## Second
1. one
2. [two](https://example.org)

### Small heading
Last <b>text</b>.
""")
    assert page.title == "My page" and "<strong>there</strong>" in page.intro
    first, second = page.sections
    assert (first.title, first.icon) == ("First", "heart")
    assert "<p>One paragraph that wraps.</p>" in first.html
    assert "<ul><li>a bullet that continues</li><li>another</li></ul>" in first.html
    assert second.icon == "" and "<ol><li>one</li>" in second.html and 'href="https://example.org"' in second.html
    assert "<h3>Small heading</h3>" in second.html and "&lt;b&gt;" in second.html and "a note" not in page.intro


def test_the_real_content_files_load():
    from web.content import load
    about, learn = load("about"), load("learn")
    assert about.section("Use of AI tools") is not None and about.section("Built by") is not None
    assert learn.title == "What is a tangled title?" and len(learn.sections) >= 4
