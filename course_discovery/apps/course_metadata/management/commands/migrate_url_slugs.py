import logging

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from course_discovery.apps.course_metadata.constants import SUBJECT_SLUG_TO_LEARN_PAGE_MAP
from course_discovery.apps.course_metadata.models import Course

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    """ Management command to migrate URL slugs for a list of courses specified by uuid.
    ./manage.py migrate_url_slugs course0uuid course1uuid ... """

    help = 'Migrate courses by uuid'

    def add_arguments(self, parser):
        parser.add_argument('courses', nargs="*", help=_('UUIDs of courses to migrate'))

    def handle(self, *args, **options):
        if options['courses'] is None or options['courses'] == []:
            raise CommandError(_('Missing required arguments'))
        self.migrate_courses(options['courses'])

    def migrate_courses(self, courseUUIDs):
        courses = Course.objects.filter(uuid__in=courseUUIDs, draft=False).select_related(
            'type'
        ).prefetch_related(
            'url_slug_history',
            'subjects',
            'authoring_organizations'
        )
        for course in courses:
            if not course.is_external_course:
                self.migrate_open_course(course)

    def migrate_open_course(self, course):
        current_course_slug = course.active_url_slug
        if current_course_slug.startswith('learn/'):
            LOG.warning(f'Course already migrated: {course.key}')
            return

        new_slug = course.add_subfolder_to_slug(current_course_slug)
        if new_slug == current_course_slug:
            return

        with transaction.atomic():
            course.set_active_url_slug(new_slug)
