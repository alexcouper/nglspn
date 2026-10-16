from __future__ import annotations

import pytest
from django.db import IntegrityError

from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    ImageFactory,
    ProjectFactory,
    article_image,
)


@pytest.mark.django_db
class TestImageOwnership:
    def test_image_with_neither_project_nor_article_is_rejected(self):
        with pytest.raises(IntegrityError):
            ImageFactory(project=None, article=None)

    def test_image_on_a_project_alone_saves(self):
        image = ImageFactory(project=ProjectFactory(), article=None)

        assert image.pk is not None

    def test_image_on_an_author_owned_article_has_no_project(self):
        image = article_image(AuthorArticleFactory())

        assert image.project_id is None
        assert image.article_id is not None

    def test_image_on_a_project_article_carries_both(self):
        article = ArticleFactory()

        image = article_image(article)

        assert image.project_id == article.project_id
        assert image.article_id == article.id


@pytest.mark.django_db
class TestImageStr:
    def test_names_the_project_when_there_is_one(self):
        image = ImageFactory(
            project=ProjectFactory(title="Demo"), original_filename="a.jpg"
        )

        assert str(image) == "Demo - a.jpg"

    def test_names_the_article_when_there_is_no_project(self):
        article = AuthorArticleFactory()

        image = article_image(article, original_filename="a.jpg")

        assert str(image) == f"article {article.id} - a.jpg"
