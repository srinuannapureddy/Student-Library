from flask import Blueprint, render_template, request, abort
from app.models.category import Category
from app.models.book import Book
from app.services.book_service import get_books_paginated, get_book_by_id

bp = Blueprint("books", __name__)


@bp.route("/")
def index():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    page = request.args.get("page", 1, type=int)

    pagination = get_books_paginated(search=search, category_id=category_id, page=page, per_page=12)
    categories = Category.query.order_by(Category.category_name.asc()).all()

    return render_template(
        "books/index.html",
        pagination=pagination,
        books=pagination.items,
        categories=categories,
        current_category=category_id,
        search_query=search
    )


@bp.route("/books/<int:book_id>")
def detail(book_id):
    book = get_book_by_id(book_id)
    if not book or book.is_archived:
        abort(404)

    return render_template("books/detail.html", book=book)

