import logging

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from course_discovery.apps.course_metadata.models import Course, CourseType

LOG = logging.getLogger(__name__)


# source: https://github.com/edx/prospectus/blob/c534f89d6f46a63a5f6c2f8f00116803172549f7/src/utils/topics.js#L214
SUBJECT_SLUG_TO_LEARN_PAGE_MAP = {
    'architecture': {
        'en': 'architecture',
        'es': 'arquitectura',
    },
    'art-culture': {
        'en': 'art',
        'es': 'arte',
    },
    'biology-life-sciences': {
        'en': 'biology',
        'es': 'biologia',
    },
    'business-management': {
        'en': 'business-administration',
        'es': 'administracion-de-empresas',
    },
    'chemistry': {
        'en': 'chemistry',
        'es': 'quimica',
    },
    'communication': {
        'en': 'business-communications',
        'es': 'comunicacion',
    },
    'computer-science': {
        'en': 'computer-programming',
        'es': 'programacion-informatica',
    },
    'data-science': {
        'en': 'data-analysis',
        'es': 'analisis-de-datos',
    },
    'design': {
        'en': 'design',
        'es': 'diseno',
    },
    'economics-finance': {
        'en': 'economics',
        'es': 'economia',
    },
    'education-teacher-training': {
        'en': 'education',
        'es': 'educacion',
    },
    'electronics': {
        'en': 'electronics',
        'es': 'ingenieria-electrica',
    },
    'energy-earth-sciences': {
        'en': 'energy',
        'es': 'energia',
    },
    'engineering': {
        'en': 'engineering',
        'es': 'ingenieria',
    },
    'environmental-studies': {
        'en': 'environmental-science',
        'es': 'medio-ambiente',
    },
    'ethics': {
        'en': 'ethics',
        'es': 'desafios-eticos',
    },
    'food-nutrition': {
        'en': 'nutrition',
        'es': 'nutricion',
    },
    'health-safety': {
        'en': 'healthcare',
        'es': 'cuidado-de-la-salud',
    },
    'history': {
        'en': 'history',
        'es': 'historia',
    },
    'humanities': {
        'en': 'humanities',
        'es': 'humanidades',
    },
    'language': {
        'en': 'language',
        'es': 'idiomas',
    },
    'law': {
        'en': 'law', 'es':
        'leyes',
    },
    'literature': {
        'en': 'literature',
        'es': 'literatura',
    },
    'math': {
        'en': 'math',
        'es': 'matematicas',
    },
    'medicine': {
        'en': 'medicine',
        'es': 'medicina',
    },
    'music': {
        'en': 'music-arts',
        'es': 'musica',
    },
    'philanthropy': {
        'en': 'humanities',
        'es': 'humanidades',
    },
    'philosophy-ethics': {
        'en': 'ethics',
        'es': 'filosofia',
    },
    'physics': {
        'en': 'physics',
        'es': 'fisica',
    },
    'science': {
        'en': 'science',
        'es': 'ciencias-naturales',
    },
    'social-sciences': {
        'en': 'social-science',
        'es': 'ciencias-sociales',
    },
}


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
        courses = Course.objects.filter(uuid__in=courseUUIDs).select_related(
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
    type_slug = course.type.slug
    if type_slug == CourseType.EXECUTIVE_EDUCATION_2U:
        return f'executive-education/{current_slug}'
    elif type_slug == CourseType.BOOTCAMP_2U:
        vertical_name = get_category_for_boot_camp(course)
        if vertical_name is not None:
            return f'boot-camps/{vertical_name}'
        else:
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


def get_category_for_boot_camp(course):
    program_name = course.title.lower()
    vertical_name = None
    if 'cyber' in program_name:
        vertical_name = 'cybersecurity'
    elif 'coding' in program_name:
        vertical_name = 'coding'
    elif 'data' in program_name:
        vertical_name = 'data-analytics'
    elif 'digital marketing' in program_name:
        vertical_name = 'digital-marketing'
    elif 'fintech' in program_name:
        vertical_name = 'fintech'
    elif 'product management' in program_name:
        vertical_name = 'product-management'
    elif 'ux/ui' in program_name:
        vertical_name = 'ux-ui-user-experience'
    elif 'technology project management' in program_name:
        vertical_name = 'tech-project-management'
    
    return vertical_name
