# backend/portal/forms.py
"""
Facade untuk form di aplikasi portal.

Form dikelompokkan per domain:
- forms_logbook: form terkait Logbook
- forms_guidance: form terkait bimbingan
- forms_pendaftaran: form pendaftaran PKL
- forms_seminar: form seminar hasil PKL
"""

from .forms_base import DateInput, TimeInput
from .forms_logbook import LogbookReviewForm, MahasiswaLogbookForm
from .forms_guidance import (
    GuidanceSessionCreateForm,
    MahasiswaGuidanceForm,
    DosenGuidanceValidationForm,
)
from .forms_pendaftaran import PendaftaranPKLMahasiswaForm
from .forms_seminar import (
    PembimbingAssessmentForm,
    SeminarAssessmentForm,
    SeminarHasilMahasiswaForm,
    SeminarPenjadwalanForm,
)

__all__ = [
    # base widgets
    "DateInput",
    "TimeInput",
    # logbook
    "LogbookReviewForm",
    "MahasiswaLogbookForm",
    # guidance
    "GuidanceSessionCreateForm",
    "MahasiswaGuidanceForm",
    "DosenGuidanceValidationForm",
    # pendaftaran PKL
    "PendaftaranPKLMahasiswaForm",
    # seminar
    "PembimbingAssessmentForm",
    "SeminarAssessmentForm",
    "SeminarHasilMahasiswaForm",
    "SeminarPenjadwalanForm",
]
