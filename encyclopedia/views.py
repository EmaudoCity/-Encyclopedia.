import random

import bleach
import markdown2
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from . import util
from .forms import EntryForm


def entry_title(title):
    return next(
        (name for name in util.list_entries() if name.casefold() == title.casefold()),
        None,
    )


def not_found(request, title):
    return render(request, "encyclopedia/error.html", {"title": title}, status=404)


@require_GET
def index(request):
    return render(request, "encyclopedia/index.html", {"entries": util.list_entries()})


@require_GET
def entry(request, title):
    canonical_title = entry_title(title)
    content = util.get_entry(canonical_title) if canonical_title is not None else None
    if content is None:
        return not_found(request, title)
    title = canonical_title
    html = bleach.clean(
        markdown2.markdown(content),
        tags=["h1", "h2", "h3", "h4", "h5", "h6", "p", "strong", "em",
              "ul", "ol", "li", "a", "blockquote", "pre", "code", "hr", "br"],
        attributes={"a": ["href", "title"]},
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return render(request, "encyclopedia/entry.html", {"title": title, "content": html})


@require_GET
def search(request):
    query = request.GET.get("q", "").strip()
    title = entry_title(query)
    if title is not None:
        return redirect("encyclopedia:entry", title=title)
    matches = [name for name in util.list_entries() if query.casefold() in name.casefold()]
    return render(request, "encyclopedia/search.html", {"query": query, "entries": matches})


@require_http_methods(["GET", "POST"])
def new_page(request):
    form = EntryForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        title = form.cleaned_data["title"]
        if entry_title(title) is not None:
            form.add_error("title", "An entry with this title already exists.")
        else:
            util.save_entry(title, form.cleaned_data["content"])
            return redirect("encyclopedia:entry", title=title)
    return render(request, "encyclopedia/form.html", {"form": form, "heading": "Create New Page"})


@require_http_methods(["GET", "POST"])
def edit_page(request, title):
    canonical_title = entry_title(title)
    content = util.get_entry(canonical_title) if canonical_title is not None else None
    if content is None:
        return not_found(request, title)
    title = canonical_title
    form = EntryForm(
        request.POST if request.method == "POST" else None,
        initial={"title": title, "content": content},
    )
    form.fields["title"].disabled = True
    if request.method == "POST" and form.is_valid():
        util.save_entry(title, form.cleaned_data["content"])
        return redirect("encyclopedia:entry", title=title)
    return render(request, "encyclopedia/form.html", {"form": form, "heading": f"Edit {title}"})


@require_GET
def random_page(request):
    entries = util.list_entries()
    if not entries:
        return not_found(request, None)
    return redirect("encyclopedia:entry", title=random.choice(entries))
