

import os
import json
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

from django.core import serializers

from django.apps import apps
from django.apps import AppConfig

from api_v2.models import *


class Command(BaseCommand):
    """Implementation for the `manage.py `export` subcommand."""

    help = 'Export all v2 model data in structured directory.'

    def add_arguments(self, parser):
        parser.add_argument("-d",
                            "--dir",
                            type=str,
                            help="Directory to write files to.")

    def handle(self, *args, **options) -> None:
        self.stdout.write('Checking if directory exists.')
        if os.path.exists(options['dir']) and os.path.isdir(options['dir']):
            self.stdout.write('Directory {} exists.'.format(options['dir']))
        else:
            self.stdout.write(self.style.ERROR(
                'Directory {} does not exist.'.format(options['dir'])))
            exit(0)

        # Start V2 output.
        rulesets = Ruleset.objects.all()
        ruleset_path = get_filepath_by_model(
            'Ruleset',
            'api_v2',
            base_path=options['dir'])
        write_queryset_data(ruleset_path, rulesets)

        license_path = get_filepath_by_model(
            'License',
            'api_v2',
            base_path=options['dir'])
        licenses = License.objects.all()
        write_queryset_data(license_path, licenses)

        # Create a folder and Publisher fixture for each pubishing org.
        for pub in Publisher.objects.order_by('key'):
            pubq = Publisher.objects.filter(key=pub.key).order_by('pk')
            pub_path = get_filepath_by_model(
                "Publisher",
                "api_v2",
                pub_key=pub.key,
                base_path=options['dir'])
            write_queryset_data(pub_path, pubq)

            # Create a Document fixture for each document.
            for doc in Document.objects.filter(publisher=pub):
                docq = Document.objects.filter(key=doc.key).order_by('pk')
                doc_path = get_filepath_by_model(
                    "Document",
                    "api_v2",
                    pub_key=pub.key,
                    doc_key=doc.key,
                    base_path=options['dir'])
                write_queryset_data(doc_path, docq)

                app_models = apps.get_models()

                for model in app_models:
                    SKIPPED_MODEL_NAMES = ['Document']
                    if model._meta.app_label == 'api_v2' and model.__name__ not in SKIPPED_MODEL_NAMES:
                        modelq = model.objects.filter(document=doc).order_by('pk')
                        model_path = get_filepath_by_model(
                            model.__name__,
                            model._meta.app_label,
                            pub_key=pub.key,
                            doc_key=doc.key,
                            base_path=options['dir'])
                        write_queryset_data(model_path, modelq)

                self.stdout.write(self.style.SUCCESS(
                    'Wrote {} to {}'.format(doc.key, doc_path)))

        self.stdout.write(self.style.SUCCESS('Data for v2 data complete.'))

def get_filepath_by_model(model_name, app_label, pub_key=None, doc_key=None, base_path=None):

    if app_label == "api_v2":
        root_folder_name = 'v2'
        root_models = ['License', 'Ruleset']
        pub_models = ['Publisher']

        if model_name in root_models:
            return "/".join((base_path,root_folder_name,model_name+".json"))

        if model_name in pub_models:
            return "/".join((base_path,root_folder_name,pub_key,model_name+".json"))

        else:
            return "/".join((base_path,root_folder_name,pub_key,doc_key,model_name+".json"))

    if app_label == "api":
        root_folder_name = 'v1'
        root_models = ['Manifest']
        doc_folder_name = doc_key

        if model_name in root_models:
            return "/".join((base_path,root_folder_name, model_name+".json"))

        else:
            return "/".join((base_path,root_folder_name, doc_key, model_name+".json"))

def write_queryset_data(filepath, queryset):
    if queryset.count() > 0:
        dir = os.path.dirname(filepath)
        if not os.path.exists(dir):
            os.makedirs(dir)

        output_filepath = filepath
        with open(output_filepath, 'w', encoding='utf-8') as f:
            serializers.serialize("json", queryset, indent=2, stream=f)
