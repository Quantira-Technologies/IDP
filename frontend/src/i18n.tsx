import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

export type Lang = "en" | "ar";
const KEY = "intel2doc_lang";

// English source string -> Arabic. Any string not present falls back to English,
// so the app keeps working while coverage grows.
const AR: Record<string, string> = {
  // ---- Navigation ----
  "Dashboard": "لوحة المعلومات",
  "Documents": "المستندات",
  "Analytics": "التحليلات",
  "Business Rules": "قواعد العمل",
  "API & Subscription": "الواجهة البرمجية والاشتراك",
  "Users": "المستخدمون",
  "Access Control": "التحكم في الوصول",
  "User Guide": "دليل المستخدم",

  // ---- Topbar / shell ----
  "Tutorials": "الشروحات",
  "Notifications": "الإشعارات",
  "Light": "فاتح",
  "Dark": "داكن",
  "Language": "اللغة",
  "Replay tutorial": "إعادة تشغيل الشرح",
  "Sign out": "تسجيل الخروج",
  "Saudi Customs · Workspace": "الجمارك السعودية · مساحة العمل",
  "permissions": "صلاحيات",
  "Open menu": "فتح القائمة",
  "Close menu": "إغلاق القائمة",
  "Collapse sidebar": "طيّ الشريط الجانبي",

  // ---- Page titles & subtitles ----
  "Operational overview — last 30 days": "نظرة تشغيلية عامة — آخر ٣٠ يومًا",
  "Upload any document — it's cleaned, fully OCR'd, and saved to your past scans":
    "ارفع أي مستند — يتم تنظيفه والتعرّف الضوئي الكامل على نصّه وحفظه في عمليات المسح السابقة",
  "Processing document": "جارٍ معالجة المستند",
  "Cleaning image → OCR → key–value → validate → route":
    "تنظيف الصورة ← التعرّف الضوئي ← استخراج القيم ← التحقق ← التوجيه",
  "Roles, modules & permissions — grant or revoke access with a click":
    "الأدوار والوحدات والصلاحيات — امنح أو اسحب الوصول بنقرة واحدة",
  "Trade insight — origins, lanes and extraction quality by country":
    "رؤى التجارة — بلدان المنشأ والمسارات وجودة الاستخراج حسب الدولة",
  "Decide what happens to each document type — auto-approve, review, or reject":
    "حدّد ما يحدث لكل نوع مستند — موافقة تلقائية أو مراجعة أو رفض",
  "API keys, plan usage and ECM/ERP connectors":
    "مفاتيح الواجهة البرمجية واستخدام الخطة وموصلات ECM/ERP",
  "How to work in intel2doc — tailored to what you can access":
    "كيفية العمل في intel2doc — مخصّص لما يمكنك الوصول إليه",
  "People and their role assignments": "الأشخاص وتعييناتهم في الأدوار",

  // ---- Dashboard ----
  "Welcome": "مرحبًا",
  "Analyze": "تحليل",
  "Documents (30d)": "المستندات (٣٠ يومًا)",
  "Straight-through": "معالجة مباشرة",
  "auto-approved": "موافق عليه تلقائيًا",
  "In review": "قيد المراجعة",
  "awaiting a human": "بانتظار مراجعة بشرية",
  "Avg confidence": "متوسط الثقة",
  "accuracy": "دقة",
  "Hours saved": "ساعات موفَّرة",
  "vs. manual review": "مقارنةً بالمراجعة اليدوية",
  "Avg speed": "متوسط السرعة",
  "per document": "لكل مستند",
  "Throughput": "الإنتاجية",
  "total vs auto-approved": "الإجمالي مقابل الموافق عليه تلقائيًا",
  "Routing mix": "توزيع التوجيه",
  "By document type": "حسب نوع المستند",
  "By workflow": "حسب سير العمل",
  "Auto-approved": "موافق عليه تلقائيًا",

  // ---- Documents ----
  "Upload document": "رفع مستند",
  "Drop a document here or click to upload": "أفلت مستندًا هنا أو انقر للرفع",
  "JPG, PNG, PDF or Word (DOCX) · auto-cleaned & fully OCR'd · QR codes captured separately":
    "JPG أو PNG أو PDF أو وورد (DOCX) · تنظيف تلقائي وتعرّف ضوئي كامل · التقاط رموز QR بشكل منفصل",
  "Past scans": "عمليات المسح السابقة",
  "Folders": "المجلدات",
  "All scans": "كل عمليات المسح",
  "Unfiled": "غير مصنّف",
  "New folder": "مجلد جديد",
  "Create folder": "إنشاء مجلد",
  "Delete folder": "حذف المجلد",
  "No scans yet. Upload a document to get started.":
    "لا توجد عمليات مسح بعد. ارفع مستندًا للبدء.",
  "Open": "فتح",
  "Delete": "حذف",
  "Back": "رجوع",
  "Move to folder": "نقل إلى مجلد",
  "Review & validate": "المراجعة والتحقق",
  "Every field is traced to the page — correct anything, then approve.":
    "كل حقل مرتبط بموضعه في الصفحة — صحّح ما تشاء ثم وافق.",
  "← Back to documents": "← العودة إلى المستندات",
  "Source": "المصدر",
  "fields": "حقول",
  "Extracted data & checks": "البيانات المستخرجة والفحوصات",
  "Approve & secure": "الموافقة والتأمين",
  "Validates and moves the document to Approved.":
    "يتحقق من المستند وينقله إلى قائمة المعتمدة.",

  // ---- Login ----
  "Every document, understood.": "كل مستند، مفهوم.",
  "Enterprise document intelligence for customs & trade — classify, extract, validate and route any invoice, certificate or declaration, with every field traced to its source.":
    "ذكاء مستندات مؤسسي للجمارك والتجارة — تصنيف واستخراج وتحقق وتوجيه أي فاتورة أو شهادة أو إقرار، مع ربط كل حقل بمصدره.",
  "OCR for any uploaded document — Arabic & English":
    "تعرّف ضوئي على أي مستند مرفوع — بالعربية والإنجليزية",
  "Business-rule validation, not just data capture":
    "تحقق وفق قواعد العمل، وليس مجرد التقاط بيانات",
  "Role-based access, audit-ready by design":
    "وصول قائم على الأدوار، جاهز للتدقيق بالتصميم",
  "Secure workspace · Saudi Customs": "مساحة عمل آمنة · الجمارك السعودية",
  "Sign in": "تسجيل الدخول",
  "Access your intel2doc workspace": "ادخل إلى مساحة عمل intel2doc",
  "Username": "اسم المستخدم",
  "Password": "كلمة المرور",
  "or": "أو",
  "Continue with": "المتابعة باستخدام",
  "Demo accounts (click to fill):": "حسابات تجريبية (انقر للتعبئة):",
  "Sign in failed": "فشل تسجيل الدخول",

  // ---- Common ----
  "Save": "حفظ",
  "Cancel": "إلغاء",
  "Copy": "نسخ",
  "Create": "إنشاء",
  "Roles": "الأدوار",

  // ---- AI status / engine badge ----
  "AI": "ذكاء اصطناعي",
  "AI extracted": "استخراج بالذكاء الاصطناعي",
  "AI fallback · OCR": "تعذّر الذكاء الاصطناعي · تعرّف ضوئي",
  "OCR": "تعرّف ضوئي",
  "Sample data": "بيانات تجريبية",
  "AI connected": "الذكاء الاصطناعي متصل",
  "AI offline": "الذكاء الاصطناعي غير متصل",
  "AI offline — using OCR fallback": "الذكاء الاصطناعي غير متصل — استخدام التعرّف الضوئي",

  // ---- Guided tour ----
  "Skip": "تخطّي",
  "Next": "التالي",
  "Done": "تم",
  "Welcome to intel2doc": "مرحبًا بك في intel2doc",
  "A quick, guided tour of your workspace — tailored to your role. We'll point out each area as we go.":
    "جولة سريعة وموجَّهة في مساحة عملك — مخصّصة لدورك. سنوضّح لك كل منطقة أثناء تقدّمنا.",
  "Your dashboard": "لوحة معلوماتك",
  "Start here for throughput, straight-through rate and confidence at a glance.":
    "ابدأ من هنا لمعرفة الإنتاجية ونسبة المعالجة المباشرة ومستوى الثقة بنظرة واحدة.",
  "One-click insights": "رؤى بنقرة واحدة",
  "Hit Analyze to generate AI insights over your operation.":
    "اضغط على «تحليل» لإنشاء رؤى بالذكاء الاصطناعي حول عملياتك.",
  "Everything you scan lives here, private to you.":
    "كل ما تمسحه ضوئيًا يُحفظ هنا، خاصٌّ بك وحدك.",
  "Scan anything": "امسح أي شيء",
  "Drop a file here — it's auto-cleaned and fully OCR'd, then routed by your business rules.":
    "أفلت ملفًا هنا — يُنظَّف تلقائيًا ويُجرى تعرّف ضوئي كامل عليه، ثم يُوجَّه وفق قواعد عملك.",
  "Past scans & folders": "عمليات المسح السابقة والمجلدات",
  "Organise consignments into folders, just like on your computer. They're private to you.":
    "نظّم الشحنات في مجلدات، تمامًا كما في حاسوبك. وهي خاصّة بك.",
  "Business rules": "قواعد العمل",
  "See (or configure) which document types are auto-approved, reviewed or rejected.":
    "اطّلع (أو اضبط) أنواع المستندات التي تُعتمد تلقائيًا أو تُراجَع أو تُرفَض.",
  "Trade analytics": "تحليلات التجارة",
  "Origins, busiest lanes and extraction confidence by country.":
    "بلدان المنشأ وأكثر المسارات ازدحامًا ومستوى ثقة الاستخراج حسب الدولة.",
  "API & ECM": "الواجهة البرمجية و ECM",
  "Generate API keys and connect ECM/ERP systems to push approved documents.":
    "أنشئ مفاتيح واجهة برمجية واربط أنظمة ECM/ERP لدفع المستندات المعتمدة.",
  "Access control": "التحكم في الوصول",
  "Grant or revoke any capability for any role — changes apply instantly.":
    "امنح أو اسحب أي صلاحية لأي دور — تُطبَّق التغييرات فورًا.",
  "Light or dark": "فاتح أو داكن",
  "Switch themes anytime — your choice is remembered.":
    "بدّل السمة في أي وقت — يُحفظ اختيارك.",
  "Replay anytime": "أعد التشغيل في أي وقت",
  "Click here whenever you want to run this tour again. That's it — enjoy!":
    "انقر هنا متى أردت إعادة هذه الجولة. هذا كل شيء — نتمنى لك تجربة ممتعة!",

  // ---- Document types (prettified) ----
  "Commercial Invoice": "فاتورة تجارية",
  "Certificate Of Origin": "شهادة منشأ",
  "House Air Waybill": "بوليصة شحن جوي",
  "Customs Declaration": "إقرار جمركي",
  "Purchase Order": "أمر شراء",
  "Goods Receipt Note": "إشعار استلام بضائع",
  "Vendor Invoice": "فاتورة مورّد",
  "Gst Certificate": "شهادة ضريبة",
  "Bank Statement": "كشف حساب بنكي",
  "Unknown": "غير معروف",

  // ---- Workflows (prettified) ----
  "Customs": "الجمارك",
  "Po2Pay": "الشراء حتى الدفع",
  "Contracts": "العقود",
  "Finance": "المالية",

  // ---- Route / status badges ----
  "auto": "تلقائي",
  "approved": "معتمد",
  "review": "مراجعة",
  "rejected": "مرفوض",
  "auto_approved": "موافق عليه تلقائيًا",
  "needs_review": "بحاجة لمراجعة",
  "Auto-approved by policy": "موافق عليه تلقائيًا حسب السياسة",

  // ---- Countries ----
  "China": "الصين", "India": "الهند", "United Arab Emirates": "الإمارات العربية المتحدة",
  "Germany": "ألمانيا", "United States": "الولايات المتحدة", "Turkey": "تركيا",
  "Egypt": "مصر", "South Korea": "كوريا الجنوبية", "Italy": "إيطاليا", "Japan": "اليابان",
  "Poland": "بولندا", "Brazil": "البرازيل", "Saudi Arabia": "السعودية", "Bahrain": "البحرين",
  "Kuwait": "الكويت", "Qatar": "قطر", "Oman": "عُمان", "Jordan": "الأردن", "Iraq": "العراق",
  "Spain": "إسبانيا", "France": "فرنسا",

  // ---- Analytics / dashboard extras ----
  "Rejected": "مرفوض",
  "people": "أشخاص",
  "No data yet": "لا توجد بيانات بعد",
  "origin → destination": "المنشأ ← الوجهة",
  "lowest needs the most review": "الأدنى يحتاج أكبر قدر من المراجعة",
  "Consignments by origin country": "الشحنات حسب بلد المنشأ",
  "Busiest trade lanes": "أكثر مسارات التجارة ازدحامًا",
  "Extraction confidence by origin country": "ثقة الاستخراج حسب بلد المنشأ",
  "Confidence distribution": "توزيع الثقة",
  "Top rule failures": "أبرز حالات فشل القواعد",
  "Reviewer performance": "أداء المراجعين",
  "Country": "الدولة", "Recommended": "موصى به",
  "auto-clear": "تخليص تلقائي",

  // ---- Business Rules page ----
  "Auto-approve": "موافقة تلقائية",
  "Review": "مراجعة",
  "Reject": "رفض",
  "Save changes": "حفظ التغييرات",
  "Saved": "تم الحفظ",
  "Minimum confidence for auto-approve": "الحد الأدنى للثقة للموافقة التلقائية",
  "Documents below this are sent to review even if their type is auto-approve.":
    "المستندات الأقل من هذا تُرسل للمراجعة حتى لو كان نوعها موافقة تلقائية.",
  "View-only. These rules decide how your scans are routed — a tenant admin configures them.":
    "للعرض فقط. هذه القواعد تحدّد كيفية توجيه عمليات المسح — يضبطها مدير المستأجر.",
  "Guidance shown to officers…": "إرشادات تظهر للموظفين…",
  "Rules saved": "تم حفظ القواعد",

  // ---- Review panel ----
  "Header fields": "الحقول الرئيسية",
  "Line items": "عناصر السطور",
  "Line": "سطر",
  "Edit": "تعديل",
  "fixed": "مُصحّح",
  "Rejected by policy": "مرفوض حسب السياسة",
  "Needs review": "بحاجة لمراجعة",
  "min confidence": "أدنى ثقة",
  "engine": "المحرك",
  "Detected table": "جدول مُكتشف",
  "rows": "صفوف",
  "Full document text": "النص الكامل للمستند",
  "lines": "أسطر",
  "Copy all": "نسخ الكل",
  "QR / barcodes": "رموز QR / الباركود",
  "Decoded value": "القيمة المفكوكة",
};

export function applyLangToDocument(lang: Lang) {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
}

export function initLang(): Lang {
  const l = (localStorage.getItem(KEY) as Lang) || "en";
  applyLangToDocument(l);
  return l;
}

interface I18nCtx {
  lang: Lang;
  dir: "rtl" | "ltr";
  t: (s: string) => string;
  num: (v: string | number) => string;
  setLang: (l: Lang) => void;
  toggle: () => void;
}

const Ctx = createContext<I18nCtx | null>(null);

const _ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
function toArabicDigits(v: string | number): string {
  return String(v).replace(/[0-9]/g, (d) => _ARABIC_DIGITS[Number(d)]);
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem(KEY) as Lang) || "en");

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(KEY, l);
    applyLangToDocument(l);
    setLangState(l);
  }, []);

  const toggle = useCallback(() => setLang(lang === "ar" ? "en" : "ar"), [lang, setLang]);

  const t = useCallback((s: string) => (lang === "ar" ? AR[s] ?? s : s), [lang]);
  const num = useCallback((v: string | number) => (lang === "ar" ? toArabicDigits(v) : String(v)), [lang]);

  const value = useMemo<I18nCtx>(
    () => ({ lang, dir: lang === "ar" ? "rtl" : "ltr", t, num, setLang, toggle }),
    [lang, t, num, setLang, toggle]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18nCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useI18n must be used within I18nProvider");
  return c;
}
