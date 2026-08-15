from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.file_security import is_path_inside, sha256_file


class Command(BaseCommand):
    help = "Audita arquivos existentes no MEDIA_ROOT e detecta caminhos fora da raiz ou symlinks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hash",
            action="store_true",
            dest="calculate_hash",
            help="Calcula SHA-256 de cada arquivo regular encontrado.",
        )

    def handle(self, *args, **options):
        root = Path(settings.MEDIA_ROOT).resolve()
        if not root.exists():
            raise CommandError(f"MEDIA_ROOT não existe: {root}")

        total = 0
        symlinks = 0
        fora = 0

        for path in root.rglob("*"):
            total += 1
            if path.is_symlink():
                symlinks += 1
                self.stdout.write(self.style.ERROR(f"SYMLINK: {path}"))
                continue

            try:
                if not is_path_inside(root, path):
                    fora += 1
                    self.stdout.write(self.style.ERROR(f"FORA_DA_RAIZ: {path}"))
                    continue
            except (OSError, ValueError) as exc:
                fora += 1
                self.stdout.write(self.style.ERROR(f"CAMINHO_INVALIDO: {path} ({exc})"))
                continue

            if options["calculate_hash"] and path.is_file():
                try:
                    digest = sha256_file(path)
                except OSError as exc:
                    self.stdout.write(self.style.ERROR(f"ERRO_HASH: {path} ({exc})"))
                else:
                    self.stdout.write(f"SHA256 {digest}  {path.relative_to(root)}")

        self.stdout.write(
            f"Auditoria concluída: entradas={total}, symlinks={symlinks}, fora_da_raiz={fora}."
        )

        if symlinks or fora:
            raise CommandError("Foram encontrados caminhos que exigem revisão de segurança.")
