import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masterdata", "0008_seminarassessment"),
    ]

    operations = [
        migrations.RenameField(
            model_name="seminarhasilpkl",
            old_name="dosen_penguji_1",
            new_name="dosen_penguji",
        ),
        migrations.RemoveField(
            model_name="seminarhasilpkl",
            name="dosen_penguji_2",
        ),
        migrations.AddField(
            model_name="seminarassessment",
            name="role",
            field=models.CharField(
                choices=[("PENGUJI", "Dosen Penguji"), ("PEMBIMBING", "Dosen Pembimbing")],
                default="PENGUJI",
                help_text="Peran penilai (penguji atau pembimbing).",
                max_length=12,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="seminarassessment",
            unique_together={("seminar", "penguji", "role")},
        ),
        migrations.AlterField(
            model_name="seminarhasilpkl",
            name="dosen_penguji",
            field=models.ForeignKey(
                blank=True,
                help_text="Hanya satu dosen penguji, tidak boleh dosen pembimbing.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="seminar_pkl_diuji",
                to="masterdata.dosen",
            ),
        ),
    ]
