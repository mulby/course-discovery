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
            if not course.active_url_slug_has_subfolder:
                new_slug = get_slug_for_course(course)
                if new_slug is None:
                    continue
                course.set_active_url_slug(new_slug)
            else:
                LOG.info(f'Course already migrated: {course.key}')


def get_slug_for_course(course):
    current_slug = course.active_url_slug
    if course.is_external_course:
        return None
    else:
        subjects = course.subjects.all()
        if len(subjects) < 1:
            logger.warning(f'Course does not have any subjects: {course.key}')
            return None
        primary_subject_slug = subjects[0].slug
        learn_slugs = SUBJECT_SLUG_TO_LEARN_PAGE_MAP.get(primary_subject_slug)
        if learn_slugs is None:
            logger.warning(f'Could not find learn slug for subject: {primary_subject_slug}')
            return None
        learn_slug_en = learn_slugs['en']

        organizations = course.authoring_organizations.all()
        if len(organizations) < 1:
            logger.warning(f'Course does not have any authoring organizations: {course.key}')
            return None
        primary_organization_key = organizations[0].key.lower()

        end_of_slug = current_slug.split('/')[-1]

        return f'learn/{learn_slug_en}/{primary_organization_key}-{end_of_slug}'
