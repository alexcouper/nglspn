import pytest
from hamcrest import assert_that, equal_to, has_length, is_

from apps.notifications.models import Notification
from apps.projects.models import UploadStatus
from services.images.django_impl.query import DjangoImageQuery, gallery_prefetch
from tests.factories import (
    ArticleFactory,
    NotificationFactory,
    ProjectFactory,
    ProjectImageFactory,
    UserFactory,
    article_image,
)


@pytest.fixture
def query():
    return DjangoImageQuery()


def assert_is_image(actual, expected) -> None:
    assert actual is not None, "expected an image, got None"
    assert_that(actual.id, equal_to(expected.id))


@pytest.mark.django_db
class TestGetGalleryImage:
    def test_returns_the_projects_own_image(self, query) -> None:
        project = ProjectFactory()
        image = ProjectImageFactory(project=project)

        assert_is_image(query.get_gallery_image(project, image.id), image)

    def test_gallery_image_excludes_an_article_upload(self, query) -> None:
        project = ProjectFactory()
        figure = article_image(ArticleFactory(project=project))

        assert_that(query.get_gallery_image(project, figure.id), is_(None))

    def test_gallery_image_excludes_an_image_on_another_project(self, query) -> None:
        elsewhere = ProjectImageFactory(project=ProjectFactory())

        assert_that(query.get_gallery_image(ProjectFactory(), elsewhere.id), is_(None))

    def test_gallery_image_honours_the_status_filter(self, query) -> None:
        project = ProjectFactory()
        pending = ProjectImageFactory(
            project=project, upload_status=UploadStatus.PENDING
        )

        assert_that(
            query.get_gallery_image(project, pending.id, status=UploadStatus.UPLOADED),
            is_(None),
        )
        assert_is_image(
            query.get_gallery_image(project, pending.id, status=UploadStatus.PENDING),
            pending,
        )
        assert_is_image(query.get_gallery_image(project, pending.id), pending)


@pytest.mark.django_db
class TestGetArticleImage:
    def test_returns_the_articles_own_upload(self, query) -> None:
        article = ArticleFactory()
        figure = article_image(article)

        assert_is_image(query.get_article_image(article, figure.id), figure)

    def test_article_image_excludes_another_articles_upload(self, query) -> None:
        project = ProjectFactory()
        mine = ArticleFactory(project=project)
        theirs_figure = article_image(ArticleFactory(project=project))

        assert_that(query.get_article_image(mine, theirs_figure.id), is_(None))

    def test_article_image_excludes_a_project_gallery_image(self, query) -> None:
        project = ProjectFactory()
        gallery = ProjectImageFactory(project=project)

        assert_that(
            query.get_article_image(ArticleFactory(project=project), gallery.id),
            is_(None),
        )

    def test_article_image_honours_the_status_filter(self, query) -> None:
        article = ArticleFactory()
        pending = article_image(article, upload_status=UploadStatus.PENDING)

        assert_that(
            query.get_article_image(article, pending.id, status=UploadStatus.UPLOADED),
            is_(None),
        )
        assert_is_image(query.get_article_image(article, pending.id), pending)


@pytest.mark.django_db
class TestGalleryPrefetch:
    def test_gallery_prefetch_narrows_a_nested_relation(self) -> None:
        project = ProjectFactory()
        gallery = ProjectImageFactory(project=project)
        article_image(ArticleFactory(project=project))
        ProjectImageFactory(project=project, upload_status=UploadStatus.PENDING)
        NotificationFactory(
            recipient=UserFactory(),
            discussion=None,
            article=ArticleFactory(project=project),
        )

        row = Notification.objects.prefetch_related(
            gallery_prefetch("article__project__images")
        ).get()

        prefetched = list(row.article.project.images.all())
        assert_that(prefetched, has_length(1))
        assert_that(prefetched[0].id, equal_to(gallery.id))
