"""Build data/eval/qa.jsonl from the hand-written questions below.

Every answerable question was written by reading the French article and its
Arabic counterpart side by side, so the same fact is asked in both languages.
The gold label is (doc_id, article number); evidence passages are pulled from
the corpus here so each question points at its source text.

  python data/eval/build_eval.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"

# (doc, article, fr_question, fr_answer, ar_question, ar_answer, tags)
# tags: "ref" = the question names the law; "numeric" = answer is a number/delay; "list" = answer is a list
ANSWERABLE = [
    ("law-2016-41", 2,
     "Dans quel délai les entreprises concernées par l'article 30 (nouveau) doivent-elles se conformer à l'obligation d'employer des personnes handicapées (loi n° 2016-41) ?",
     "Dans un délai d'une année à compter de l'entrée en vigueur de la loi.",
     "ما هو الأجل الذي يتعين فيه على المنشآت المعنية بالفصل 30 (جديد) الامتثال لإلزامية تشغيل الأشخاص ذوي الإعاقة وفق القانون عدد 41 لسنة 2016؟",
     "في أجل سنة من تاريخ دخول القانون حيز التنفيذ.", "ref numeric"),
    ("law-2018-29", 188,
     "Par quel acte sont instituées les régies de recettes et les régies d'avances d'une collectivité locale ?",
     "Par arrêté du ministre des Finances (ou de son délégué), sur proposition du président de la collectivité locale.",
     "بأي نص تُحدث وكالات المقابيض ووكالات الدفوعات بالجماعات المحلية؟",
     "بقرار من وزير المالية أو من يفوّض له ذلك، باقتراح من رئيس الجماعة المحلية.", ""),
    ("law-2016-53", 35,
     "En cas de désaccord sur l'indemnité d'expropriation, que peut demander l'exproprié au tribunal de première instance en attendant un jugement définitif (loi n° 2016-53) ?",
     "Un jugement l'autorisant à percevoir le montant consigné en sa faveur, dans la limite de l'offre de l'expropriant et sous réserve des exigences d'inscription ou de publicité des articles 36 et 38.",
     "في صورة عدم الاتفاق رضائيا على قيمة غرامة الانتزاع، ماذا يمكن للمنتزع منه أن يطلب من المحكمة الابتدائية في انتظار صدور حكم بات (القانون عدد 53 لسنة 2016)؟",
     "الحكم له بسحب المبلغ المؤمَّن لفائدته في حدود عرض المنتزع وبشرط استيفاء موجبات الترسيم أو الإشهار المشار إليها بالفصلين 36 و38.", "ref"),
    ("law-2015-32", 4,
     "Quels emplois sont considérés comme emplois supérieurs diplomatiques selon la loi n° 2015-32 ?",
     "Ambassadeur, délégué ou représentant permanent, chargé d'affaires chef de mission, chef de mission diplomatique ou permanente adjoint, consul général, consul, secrétaire général du ministère des affaires étrangères et directeurs généraux supervisant les services diplomatiques du ministère.",
     "ما هي الوظائف التي تُعد وظائف عليا دبلوماسية وفق القانون عدد 32 لسنة 2015؟",
     "سفير، مندوب دائم أو ممثل دائم، قائم بالأعمال رئيس بعثة، رئيس بعثة دبلوماسية أو دائمة مساعد، قنصل عام، قنصل، كاتب عام الوزارة المكلفة بالشؤون الخارجية، والمديرون العامون المشرفون على المصالح الدبلوماسية بالوزارة.", "ref list"),
    ("law-2016-22", 24,
     "Dans quels cas un organisme peut-il refuser l'accès à l'information selon la loi organique sur le droit d'accès à l'information ?",
     "Uniquement lorsque l'accès causerait un préjudice à la sécurité ou à la défense nationale, aux relations internationales y liées, ou aux droits du tiers (vie privée, données personnelles, propriété intellectuelle).",
     "في أي الحالات يمكن للهيكل المعني رفض طلب النفاذ إلى المعلومة وفق القانون الأساسي المتعلق بالحق في النفاذ إلى المعلومة؟",
     "فقط إذا كان ذلك يؤدي إلى إلحاق ضرر بالأمن العام أو بالدفاع الوطني أو بالعلاقات الدولية المتصلة بهما أو بحقوق الغير في حماية حياته الخاصة ومعطياته الشخصية وملكيته الفكرية.", "list"),
    ("law-2026-8", 41,
     "Quelle amende encourt celui qui organise sciemment un spectacle artistique sans respecter les conditions de l'article 21 de la loi relative à l'artiste et aux métiers artistiques ?",
     "Une amende de 5 000 à 10 000 dinars (même peine pour le propriétaire ou gestionnaire de l'espace), doublée en cas de récidive.",
     "ما هي العقوبة المستوجبة على من يتعمد تنظيم عرض فني دون احترام الشروط الواردة بالفصل 21 من القانون المتعلق بالفنان والمهن الفنية؟",
     "خطية تتراوح بين 5000 دينار و10000 دينار، ويعاقب بنفس العقوبة صاحب الفضاء أو صاحب الحق في التصرف فيه، وتضاعف في صورة العود.", "numeric"),
    ("law-2015-37", 8,
     "Quels sont les délais du dépôt légal pour les livres et les œuvres musicales, d'une part, et pour les œuvres périodiques, d'autre part (loi organique n° 2015-37) ?",
     "Un mois à compter de la mise à disposition du public pour les œuvres musicales, films, œuvres audio et audiovisuelles et livres ; 48 heures pour les œuvres périodiques et non périodiques et autres œuvres de l'article 4.",
     "ما هي آجال الإيداع القانوني بالنسبة إلى الكتب والمؤلفات الموسيقية من جهة وإلى المصنفات الدورية من جهة أخرى (القانون الأساسي عدد 37 لسنة 2015)؟",
     "شهر من تاريخ وضع المصنف على ذمة العموم بالنسبة إلى المؤلفات الموسيقية والأفلام السينمائية والمؤلفات السمعية والسمعية البصرية والكتب، و48 ساعة بالنسبة إلى المصنفات الدورية وغير الدورية وغيرها.", "ref numeric"),
    ("law-2016-34", 26,
     "Dans quels cas un bulletin de vote est-il nul lors de l'élection des membres du Conseil supérieur de la magistrature (loi organique n° 2016-34) ?",
     "Lorsqu'il n'est pas établi pour le scrutin, contient plus de candidats que prévu pour chaque ordre ou grade, n'exprime pas clairement la volonté de l'électeur, est contraire à la confidentialité ou à la liberté du suffrage, ou méconnaît le principe de parité (sauf insuffisance de candidats d'un sexe). Les bulletins blancs ne comptent pas.",
     "متى تعتبر ورقة التصويت ملغاة في انتخاب أعضاء المجلس الأعلى للقضاء (القانون الأساسي عدد 34 لسنة 2016)؟",
     "إذا كانت غير معدة للغرض أو تحتوي أكثر من العدد المقرر لكل رتبة أو صنف أو لا تعبر بوضوح عن إرادة الناخب أو تتعارض مع سرية أو حرية الاقتراع أو لا تحترم مبدأ التناصف (باستثناء حالة عدم كفاية مترشحين من أحد الجنسين). ولا تحتسب الأوراق البيضاء.", "ref list"),
    ("law-2020-30", 16,
     "Que prévoit la loi relative à l'économie sociale et solidaire pour les commandes publiques ?",
     "Un pourcentage des commandes publiques est réservé aux entreprises de l'économie sociale et solidaire, dans le respect de la concurrence et de l'égalité des chances ; le pourcentage et les conditions sont fixés par décret gouvernemental.",
     "ماذا ينص القانون المتعلق بالاقتصاد الاجتماعي والتضامني بخصوص الطلبات العمومية؟",
     "تخصص نسبة من الطلبات العمومية لفائدة مؤسسات الاقتصاد الاجتماعي والتضامني مع احترام مبدأ المنافسة وتكافؤ الفرص، وتضبط النسبة والشروط بأمر حكومي.", ""),
    ("law-2026-5", 1,
     "Sur quelle durée maximale les banques doivent-elles rééchelonner les créances bancaires des agriculteurs, et quel pourcentage du principal faut-il payer au dépôt de la demande (loi n° 2026-5) ?",
     "Sur une période maximale de 7 ans dont une année de grâce, à condition de payer 5 % du principal de la dette lors du dépôt de la demande.",
     "ما هي المدة القصوى لإعادة جدولة الديون البنكية للفلاحين وما هي النسبة الواجب دفعها من أصل الدين عند تقديم مطلب التسوية (القانون عدد 5 لسنة 2026)؟",
     "مدة أقصاها 7 سنوات منها سنة إمهال، شريطة دفع 5% من قيمة أصل الدين عند تقديم مطلب التسوية.", "ref numeric"),
    ("law-2017-54", 5,
     "À qui le conseil créé par la loi n° 2017-54 transmet-il son rapport annuel et quand ?",
     "Une copie est transmise au Président de la République, au chef du gouvernement et au président de l'ARP, au cours du premier trimestre de l'année suivante ; le rapport est publié sur le site du conseil.",
     "إلى من يوجه المجلس المحدث بالقانون عدد 54 لسنة 2017 تقريره السنوي ومتى؟",
     "يوجه نسخة منه إلى رئيس الجمهورية ورئيس الحكومة ورئيس مجلس نواب الشعب خلال الثلاثية الأولى من السنة الموالية، وينشر على الموقع الإلكتروني للمجلس.", "ref"),
    ("law-2018-38", 5,
     "Par quel arrêté est approuvé le règlement intérieur de la mutuelle créée par la loi n° 2018-38 ?",
     "Par arrêté conjoint du ministre de la justice, du ministre des finances et du ministre des affaires sociales.",
     "بأي قرار تتم المصادقة على النظام الداخلي للتعاونية المحدثة بالقانون عدد 38 لسنة 2018؟",
     "بقرار مشترك من وزير العدل ووزير المالية ووزير الشؤون الاجتماعية.", "ref"),
    ("law-2016-31", 5,
     "Par quel arrêté conjoint est approuvé le règlement intérieur de la mutuelle créée par la loi n° 2016-31 ?",
     "Par arrêté conjoint du ministre de la défense nationale, du ministre des finances et du ministre des affaires sociales.",
     "بأي قرار مشترك تتم المصادقة على النظام الداخلي للتعاونية المحدثة بالقانون عدد 31 لسنة 2016؟",
     "بقرار مشترك من وزير الدفاع الوطني ووزير المالية ووزير الشؤون الاجتماعية.", "ref"),
    ("law-2020-37", 27,
     "Sous quelle forme les contributeurs peuvent-ils participer à une société présentée sur une plateforme de « Crowdfunding » ?",
     "Sous forme de souscription à des actions ordinaires, des sukuks ou des obligations.",
     "في أي شكل يجب أن تكون مساهمات المشاركين في شركة معروضة على منصة التمويل التشاركي؟",
     "في شكل اكتتاب في أسهم عادية أو صكوك أو رقاع.", "list"),
    ("law-2018-51", 21,
     "Comment l'Instance mène-t-elle ses enquêtes et ses séances d'audition afin de protéger les témoins et les victimes (loi organique n° 2018-51) ?",
     "Confidentiellement, en assurant la protection de l'intégrité physique et du parcours professionnel des témoins et victimes, notamment des enfants.",
     "كيف تجري الهيئة بحثها وجلسات الاستماع لحماية الشهود والضحايا (القانون الأساسي عدد 51 لسنة 2018)؟",
     "في كنف السرية، مع ضمان حماية الحرمة الجسدية والمسار المهني للشهود والضحايا وخاصة الأطفال.", "ref"),
    ("law-2014-16", 148,
     "Dans quel délai l'Instance proclame-t-elle les résultats définitifs des élections (loi organique n° 2014-16) ?",
     "Dans un délai de 48 heures à compter de la réception du dernier arrêté de l'assemblée plénière du tribunal administratif concernant les recours, ou après expiration des délais de recours.",
     "في أي أجل تصرح الهيئة بالنتائج النهائية للانتخابات (القانون الأساسي عدد 16 لسنة 2014)؟",
     "في أجل 48 ساعة من توصلها بآخر حكم صادر عن الجلسة العامة القضائية للمحكمة الإدارية في خصوص الطعون أو بعد انقضاء أجل الطعن.", "ref numeric"),
    ("law-2015-33", 4,
     "Comment se fait la nomination aux emplois civils supérieurs autres que ceux prévus par l'article 2 de la loi n° 2015-33 ?",
     "Par arrêté du chef du gouvernement sur proposition du ministre exerçant le pouvoir hiérarchique ou de tutelle, sauf pour les entreprises publiques, les établissements publics non administratifs et les instances de régulation non prévues par la Constitution.",
     "كيف يتم التعيين في الوظائف المدنية العليا غير المنصوص عليها بالفصل 2 من القانون عدد 33 لسنة 2015؟",
     "بقرار من رئيس الحكومة وباقتراح من الوزير الذي يمارس سلطة التسلسل أو الإشراف الإداري، باستثناء المنشآت العمومية والمؤسسات العمومية غير الإدارية والهيئات التعديلية غير المنصوص عليها بالدستور.", "ref"),
    ("law-2016-33", 1,
     "Sous quelle forme juridique peuvent être créés les centres de formation et de préparation de l'élite sportive ?",
     "Sous forme d'établissements publics à caractère administratif dotés de la personnalité morale et de l'autonomie financière, sous la tutelle du ministère chargé des sports.",
     "في أي شكل قانوني يمكن إحداث مراكز تكوين وإعداد رياضيي النخبة؟",
     "في شكل مؤسسات عمومية ذات صبغة إدارية تتمتع بالشخصية المعنوية والاستقلال المالي وتخضع لإشراف الوزارة المكلفة بالرياضة.", ""),
    ("law-2018-47", 16,
     "Dans quel délai les agents de l'instance doivent-ils respecter le code de conduite approuvé par le conseil de l'instance (loi organique n° 2018-47) ?",
     "Dans un délai n'excédant pas six mois à compter de la date de prise de fonctions de l'instance.",
     "في أي أجل يلتزم أعوان الهيئة بمدونة السلوك التي يصادق عليها مجلس الهيئة (القانون الأساسي عدد 47 لسنة 2018)؟",
     "في أجل لا يتجاوز ستة أشهر من تاريخ مباشرة الهيئة لمهامها.", "ref numeric"),
    ("law-2021-37", 12,
     "À quelle fréquence et selon quelles modalités le salaire d'un travailleur domestique est-il payé ?",
     "Une fois par mois sauf accord contraire, directement au travailleur, contre récépissé ou tout moyen laissant une trace écrite (identité, durée du travail, montant, date de paiement).",
     "كم مرة يدفع أجر العامل المنزلي وبأي طريقة؟",
     "مرة في الشهر ما لم يتفق الطرفان على خلاف ذلك، ويتم الدفع مباشرة للعامل مقابل وصل أو أية وسيلة تترك أثرا كتابيا.", ""),
    ("law-2017-59", 39,
     "Dans quel délai les candidats peuvent-ils former un recours contre les décisions de la commission parlementaire (loi organique n° 2017-59) ?",
     "Dans un délai de sept jours à compter de la publication de la liste des candidats, devant la Cour administrative d'appel de Tunis.",
     "في أي أجل يمكن للمترشحين الطعن في قرارات اللجنة البرلمانية (القانون الأساسي عدد 59 لسنة 2017)؟",
     "في أجل سبعة أيام من تاريخ نشر قائمة المترشحين أمام المحكمة الإدارية الاستئنافية بتونس.", "ref numeric"),
    ("law-2016-35", 35,
     "Dans quel délai la Banque centrale doit-elle aliéner les immeubles acquis pour garantir le recouvrement de créances douteuses ?",
     "Dans un délai de deux ans, à moins qu'ils ne soient utilisés pour les besoins de son exploitation.",
     "في أي أجل يجب على البنك المركزي التفويت في العقارات المشتراة لضمان استخلاص الديون المشكوك فيها؟",
     "في ظرف عامين، إلا إذا تم استعمالها من قبله لحاجيات الاستغلال.", "numeric"),
    ("law-2019-10", 11,
     "Comment sont fixés le mode de calcul et le montant des transferts financiers directs mensuels aux catégories pauvres (loi organique n° 2019-10) ?",
     "Par arrêté conjoint du ministre chargé des affaires sociales et du ministre chargé des finances.",
     "كيف تضبط طريقة احتساب ومقدار التحويلات المالية المباشرة الشهرية للفئات الفقيرة (القانون الأساسي عدد 10 لسنة 2019)؟",
     "بقرار مشترك من الوزير المكلف بالشؤون الاجتماعية والوزير المكلف بالمالية.", "ref"),
    ("law-2015-50", 3,
     "À qui la Cour constitutionnelle présente-t-elle son rapport annuel et quand ?",
     "Au Président de la République, au chef du gouvernement et au président de l'ARP, au cours du deuxième trimestre suivant l'année du rapport ; il est publié au JORT et sur son site.",
     "إلى من تقدم المحكمة الدستورية تقريرها السنوي ومتى؟",
     "إلى رئيس الجمهورية ورئيس الحكومة ورئيس مجلس نواب الشعب خلال الثلاثية الثانية الموالية لسنة التقرير، ويُنشر بالرائد الرسمي وبموقعها الإلكتروني.", ""),
    ("law-2025-4", 5,
     "Qui est l'ordonnateur des recettes et des dépenses du budget des conseils locaux, régionaux et de districts (loi organique n° 2025-4) ?",
     "Le président du conseil.",
     "من هو آمر قبض وصرف ميزانية المجالس المحلية والجهوية ومجالس الأقاليم (القانون الأساسي عدد 4 لسنة 2025)؟",
     "رئيس المجلس.", "ref"),
    ("law-2016-24", 6,
     "Quel est le montant des crédits délégués aux postes diplomatiques et consulaires à l'étranger pour l'année 2011, selon la loi de règlement du budget n° 2016-24 ?",
     "95 215 886,342 dinars (dépenses : 92 119 548,484 dinars ; excédent : 3 096 337,858 dinars).",
     "ما هو مبلغ الاعتمادات المفوضة إلى المراكز الدبلوماسية والقنصلية بالخارج لسنة 2011 وفق قانون ختم الميزانية عدد 24 لسنة 2016؟",
     "95 215 886,342 دينار (الدفوعات 92 119 548,484 دينار والفائض 3 096 337,858 دينار).", "ref numeric"),
    ("law-2024-20", 6,
     "Quel est le montant des crédits délégués aux postes diplomatiques et consulaires à l'étranger pour l'année 2019, selon la loi n° 2024-20 portant règlement du budget ?",
     "217 179 625,875 dinars (dépenses : 210 271 431,161 dinars ; excédent : 6 908 194,714 dinars).",
     "ما هو مبلغ الاعتمادات المفوضة إلى المراكز الدبلوماسية والقنصلية بالخارج لسنة 2019 وفق القانون عدد 20 لسنة 2024 المتعلق بختم الميزانية؟",
     "217 179 625,875 دينار (الدفوعات 210 271 431,161 دينار والفائض 6 908 194,714 دينار).", "ref numeric"),
    ("law-2017-13", 3,
     "Quelle amende encourt le tuteur qui s'abstient d'inscrire son pupille ayant interrompu précocement sa scolarité au cycle préparatoire ou à la formation professionnelle (loi n° 2017-13) ?",
     "Une amende de 20 à 200 dinars (portée à 400 dinars en cas de récidive).",
     "ما هي الخطية المستوجبة على الولي الذي يمتنع عن إلحاق منظوره المنقطع مبكرا عن التعليم بالمرحلة التحضيرية أو بالتكوين المهني (القانون عدد 13 لسنة 2017)؟",
     "خطية من 20 إلى 200 دينار، وترفع إلى 400 دينار في صورة العود.", "ref numeric"),
    ("law-2015-11", 15,
     "De combien est réduite la valeur de l'amende pour les bâtiments situés dans les zones d'encouragement du développement régional (loi n° 2015-11) ?",
     "De 30 %.",
     "بكم يخفض مقدار الغرامة بالنسبة إلى البناءات المتواجدة داخل مناطق تشجيع التنمية الجهوية (القانون عدد 11 لسنة 2015)؟",
     "بنسبة 30%.", "ref numeric"),
    ("law-2025-9", 6,
     "Que deviennent les contrats de travail à durée déterminée qui ne relèvent pas des cas exceptionnels prévus par le Code du travail (loi n° 2025-9) ?",
     "Ils se transforment en contrats à durée indéterminée, indépendamment de leur date d'expiration ou de l'achèvement des travaux ; cela vaut aussi pour les contrats en cours ou rompus après le 14 mars 2025.",
     "ماذا يحدث لعقود الشغل معينة المدة غير المشمولة بالحالات الاستثنائية الواردة بمجلة الشغل (القانون عدد 9 لسنة 2025)؟",
     "تتحول إلى عقود شغل غير معينة المدة دون اعتبار لآجال انتهائها أو إنهاء الأعمال موضوع العقد، ويشمل ذلك العقود الجارية أو التي قطعت بعد 14 مارس 2025.", "ref"),
    ("law-2013-48", 8,
     "Quelle unité chaque fonds d'investissement islamique doit-il avoir (loi n° 2013-48) ?",
     "Une unité d'audit charaïque interne chargée de contrôler la conformité du fonds aux normes charaïques et de faire des rapports périodiques au comité de contrôle charaïque et au conseil.",
     "ما هي الوحدة التي يتعين أن تكون لدى كل صندوق استثمار إسلامي (القانون عدد 48 لسنة 2013)؟",
     "وحدة للتدقيق الشرعي الداخلي تتولى فحص ومراقبة التزام الصندوق بالمعايير الشرعية وإعداد تقارير دورية ترفع لهيئة الرقابة الشرعية ومجلس الإدارة أو المراقبة.", "ref"),
    ("law-2019-25", 66,
     "Qui est tenu de prêter main-forte aux agents de contrôle lors de leurs missions de sécurité sanitaire des denrées alimentaires (loi n° 2019-25) ?",
     "Les autorités civiles, sécuritaires et militaires, lorsqu'elles sont sollicitées ; les entrepreneurs de transport ne doivent pas entraver les contrôles.",
     "من يتعين عليه تقديم يد المساعدة لأعوان المراقبة عند قيامهم بمهامهم في مجال السلامة الصحية للأغذية (القانون عدد 25 لسنة 2019)؟",
     "السلط المدنية والأمنية والعسكرية عند الطلب، وعلى أصحاب مؤسسات النقل ألا يعرقلوا عمليات المراقبة.", "ref"),
    ("law-2016-32", 7,
     "De quoi sont composées les ressources de chaque mutuelle créée par la loi n° 2016-32 ?",
     "Des cotisations retenues sur les traitements des adhérents et celles des retraités, des subventions éventuelles de l'Etat, des revenus des biens de la mutuelle, des dons et legs autorisés par le ministre concerné et des revenus des activités diverses.",
     "مم تتكون موارد كل تعاونية محدثة بالقانون عدد 32 لسنة 2016؟",
     "من مبالغ الانخراط المحجوزة من مرتبات المنخرطين واشتراكات المتقاعدين، والمنح التي تدفعها الدولة عند الاقتضاء، ومداخيل أملاك التعاونية، والهبات والتبرعات بترخيص من الوزير المعني، ومداخيل الأنشطة المختلفة.", "ref list"),
    ("law-2018-35", 5,
     "Que doivent faire les entreprises des rapports relatifs aux projets de responsabilité sociétale mis en œuvre (loi n° 2018-35) ?",
     "Elles les rendent publics et veillent à leur vulgarisation.",
     "ماذا يتعين على المؤسسات بخصوص التقارير المتعلقة ببرامج المسؤولية المجتمعية المنفذة (القانون عدد 35 لسنة 2018)؟",
     "تسهر على نشر هذه التقارير.", "ref"),
    ("law-2018-46", 29,
     "Quel est le sort des cadeaux dont la valeur dépasse le seuil prévu à l'article 28 de la loi n° 2018-46 relative à la déclaration de patrimoine ?",
     "Ils sont considérés comme propriété privée de l'Etat.",
     "ما مآل الهدايا التي تتجاوز الحد المشار إليه بالفصل 28 من القانون عدد 46 لسنة 2018 المتعلق بالتصريح بالمكاسب؟",
     "تعتبر ملكا خاصا للدولة.", "ref"),
    ("law-2019-15", 19,
     "Quelles entités sont considérées comme des missions spéciales dans la loi organique du budget (loi organique n° 2019-15) ?",
     "L'ARP, le Conseil supérieur de la magistrature, la Cour constitutionnelle, les instances juridictionnelles autonomes, les instances constitutionnelles indépendantes, les charges de financement et les dépenses imprévues et non réparties.",
     "ما هي الجهات التي تعتبر مهمات خاصة في القانون الأساسي للميزانية (القانون الأساسي عدد 15 لسنة 2019)؟",
     "مجلس نواب الشعب، المجلس الأعلى للقضاء، المحكمة الدستورية، الهياكل القضائية ذات الاستقلالية الإدارية والمالية، الهيئات الدستورية المستقلة، نفقات التمويل، والنفقات الطارئة وغير الموزعة.", "ref list"),
    ("law-2016-61", 52,
     "Où les personnes bénéficiant de protection peuvent-elles élire domicile lorsqu'elles sont appelées à déposer (loi organique n° 2016-61) ?",
     "Près du procureur de la République territorialement compétent, qui consigne leur identité et adresse réelle sur un registre confidentiel.",
     "أين يمكن للأشخاص المشمولين بالحماية تعيين محل مخابرتهم عند دعوتهم للإدلاء بتصريحاتهم (القانون الأساسي عدد 61 لسنة 2016)؟",
     "لدى وكيل الجمهورية المختص ترابيا، وتضمن هوياتهم ومقراتهم الأصلية بدفتر سري.", "ref"),
    ("law-2019-60", 3,
     "Comment l'Instance du développement durable renforce-t-elle la démocratie participative (loi organique n° 2019-60) ?",
     "Par des mécanismes fixés dans son règlement intérieur, cadre de concertation avec associations, partis, organisations professionnelles et représentants des collectivités locales ; elle peut organiser des consultations nationales et des tables rondes.",
     "كيف تدعم هيئة التنمية المستدامة الديمقراطية التشاركية (القانون الأساسي عدد 60 لسنة 2019)؟",
     "بآليات يضبطها نظامها الداخلي توفر إطارا للتشاور والحوار مع الجمعيات والأحزاب والمنظمات المهنية وممثلي الجماعات المحلية، ويمكنها تنظيم استشارات وطنية وحلقات نقاش.", "ref"),
    ("law-2018-54", 2,
     "Quelle est la mission des établissements publics de la catégorie créée par la loi n° 2018-54 ?",
     "Réaliser des travaux de sondages hydrauliques et de forage de puits profonds pour le compte d'instances publiques et privées, intervenir sur les puits vétustes et creuser des puits dans les zones éloignées.",
     "ما هي مهام المؤسسات العمومية المحدثة ضمن الصنف المحدث بالقانون عدد 54 لسنة 2018؟",
     "إنجاز أشغال التنقيب عن المياه وحفر الآبار العميقة لحساب الهيئات العمومية والخاصة، والتدخل في الآبار القديمة والمعطلة، وحفر الآبار في المناطق البعيدة.", "ref"),
    ("law-2025-5", 4,
     "À partir de quelle date les dispositions de la loi n° 2025-5 prennent-elles effet ?",
     "À compter du 19 avril 2024.",
     "ابتداء من أي تاريخ يجري العمل بأحكام القانون عدد 5 لسنة 2025؟",
     "ابتداء من 19 أفريل 2024.", "ref numeric"),
    ("law-2015-38", 3,
     "Que perçoivent le conjoint survivant et les enfants en cas de décès du Président de la République (loi n° 2015-38) ?",
     "Les pensions des veuves et des orphelins, calculées sur la base de la rente viagère du Président après cessation de ses fonctions, et ils conservent les prestations sanitaires.",
     "ماذا ينتفع به القرين الباقي على قيد الحياة والأبناء عند وفاة رئيس الجمهورية (القانون عدد 38 لسنة 2015)؟",
     "جرايات الأرامل والأيتام المحتسبة على أساس الجراية العمرية المخولة لرئيس الجمهورية المنتهية مهامه، ويواصلون الانتفاع بالعناية الصحية.", "ref"),
    ("law-2020-38", 3,
     "Selon quels critères sont classés les candidats au recrutement direct d'un individu par famille de chômeurs (loi n° 2020-38) ?",
     "Par ordre de mérite selon l'âge du diplômé et l'année d'obtention du diplôme.",
     "وفق أي مقياسين يتم ترتيب المترشحين للانتداب المباشر لفرد من كل عائلة عاطلة عن العمل (القانون عدد 38 لسنة 2020)؟",
     "ترتيبا تفاضليا وفق مقياسي سن المتخرج وسنة التخرج.", "ref"),
    ("law-2015-26", 79,
     "Quels soins bénéficient aux victimes du terrorisme selon la loi organique n° 2015-26 ?",
     "La gratuité des soins et traitements dans les établissements publics de santé, ainsi que l'assistance médicale et sociale assurée par la Commission nationale de lutte contre le terrorisme.",
     "بأي رعاية صحية يتمتع ضحايا الإرهاب وفق القانون الأساسي عدد 26 لسنة 2015؟",
     "مجانية العلاج والتداوي بالهياكل الصحية العمومية، مع ضمان اللجنة الوطنية لمكافحة الإرهاب للمساعدة الطبية والاجتماعية.", "ref"),
    ("law-2024-33", 15,
     "Que fait la commune lorsque les propriétaires n'ont pas exécuté la décision d'évacuation après le délai de trois mois (loi n° 2024-33 sur les bâtiments menaçant ruine) ?",
     "Elle se substitue obligatoirement à eux pour évacuer le bâtiment, à leurs frais.",
     "ماذا تفعل البلدية إذا لم ينفذ المالكون قرار الإخلاء بعد انقضاء أجل الثلاثة أشهر (القانون عدد 33 لسنة 2024 المتعلق بالبنايات المتداعية للسقوط)؟",
     "تتولى وجوبا الحلول محلهم للقيام بإخلاء البناية وعلى نفقتهم.", "ref numeric"),
    ("law-2024-11", 13,
     "Les contrôles antidopage doivent-ils être notifiés au sportif à l'avance (loi n° 2024-11 relative à la lutte contre le dopage) ?",
     "Non : ils sont conduits en ou hors compétition sans notification préalable, sauf circonstances exceptionnelles et justifiées.",
     "هل يجب إعلام الرياضي مسبقا بعمليات مراقبة المنشطات (القانون عدد 11 لسنة 2024 المتعلق بمكافحة المنشطات)؟",
     "لا، تجرى داخل المسابقات أو خارجها دون سابق إعلام للرياضي إلا في حالات استثنائية ومبررة.", "ref"),
    ("law-2017-58", 6,
     "Quelles pratiques discriminatoires à l'égard des femmes l'Etat doit-il éliminer selon la loi organique n° 2017-58 ?",
     "Toutes les pratiques discriminatoires, notamment en matière de rémunération et de couverture sociale, et il doit interdire l'exploitation économique des femmes et leur emploi dans des conditions pénibles, dégradantes ou préjudiciables.",
     "ما هي الممارسات التمييزية ضد المرأة التي يجب على الدولة القضاء عليها وفق القانون الأساسي عدد 58 لسنة 2017؟",
     "كل الممارسات التمييزية خاصة على مستوى الأجر والتغطية الاجتماعية، ومنع الاستغلال الاقتصادي للمرأة وتشغيلها في ظروف قاسية أو مهينة أو مضرة.", "ref"),
    ("law-2016-48", 16,
     "Qu'est-ce qu'un dépôt d'investissement au sens de la loi n° 2016-48 relative aux banques ?",
     "Les montants logés dans un compte bancaire en vertu d'un contrat de Moudaraba ou de Wakala pour être investis en actifs sur une période déterminée ; la banque ne garantit aucune perte sauf négligence ou manquement établi.",
     "ما المقصود بالودائع الاستثمارية على معنى القانون عدد 48 لسنة 2016 المتعلق بالبنوك؟",
     "المبالغ التي يضعها أصحابها في حساب لدى بنك بمقتضى عقد مضاربة أو وكالة لاستثمارها لمدة محددة في أصول، ولا يضمن البنك أية خسارة ما لم يثبت تقصيره أو مخالفته للشروط التعاقدية.", "ref"),
    ("law-2015-36", 12,
     "Qu'apprécie le conseil de la concurrence pour un projet de concentration économique (loi n° 2015-36) ?",
     "Si le projet apporte au progrès technique ou économique une contribution suffisante pour compenser les atteintes à la concurrence, en tenant compte de la compétitivité des entreprises nationales face à la concurrence internationale.",
     "ما الذي ينظر فيه مجلس المنافسة بشأن مشروع تركيز اقتصادي (القانون عدد 36 لسنة 2015)؟",
     "مدى مساهمة المشروع في التقدم التقني أو الاقتصادي قصد ضمان التعويض الكافي عن الإخلال بالمنافسة، مع مراعاة تنافسية المؤسسات الوطنية أمام المنافسة الدولية.", "ref"),
    ("law-2018-9", 21,
     "Dans quels cas l'huissier de justice est-il radié du tableau (loi organique n° 2018-9) ?",
     "En cas de démission, d'incapacité physique totale, de décès ou de sanction disciplinaire, par décision du ministre de la justice.",
     "في أي الحالات يقع الشطب على العدل المنفذ من الجدول (القانون الأساسي عدد 9 لسنة 2018)؟",
     "الاستقالة، العجز البدني التام، الوفاة، أو بموجب عقوبة تأديبية، وذلك بقرار من وزير العدل.", "ref list"),
    ("law-2014-48", 5,
     "Qui prend en charge les pensions de retraite et les contributions de bonification dans le cadre de la retraite facultative de la loi n° 2014-48 ?",
     "La société, et ces montants sont déduits de l'assiette de l'impôt sur les sociétés de l'année où ils ont été payés à la caisse.",
     "من يتكفل بمبالغ الجرايات ومساهمات التنفيل في إطار الإحالة الاختيارية على التقاعد بالقانون عدد 48 لسنة 2014؟",
     "الشركة، وتطرح هذه المبالغ من قاعدة الضريبة على الشركات في سنة دفعها للصندوق.", "ref"),
]

# Questions the corpus cannot answer: the right behaviour is "I don't know".
UNANSWERABLE = [
    ("Quel est le salaire minimum garanti (SMIG) en Tunisie en 2025 ?", "ما هو الأجر الأدنى المضمون في تونس سنة 2025؟"),
    ("Quelle est la capitale de la France ?", "ما هي عاصمة فرنسا؟"),
    ("Quelles pièces faut-il fournir pour obtenir un passeport tunisien ?", "ما هي الوثائق المطلوبة للحصول على جواز سفر تونسي؟"),
    ("Quels sont les horaires d'ouverture des tribunaux de première instance ?", "ما هي أوقات عمل المحاكم الابتدائية؟"),
    ("Quelle est la durée du congé de maternité des salariées du secteur privé ?", "ما هي مدة عطلة الأمومة للأجيرات في القطاع الخاص؟"),
    ("Comment préparer un couscous tunisien traditionnel ?", "كيف يُحضَّر الكسكسي التونسي التقليدي؟"),
    ("Quel est l'âge minimum légal du mariage en Tunisie ?", "ما هو السن الأدنى القانوني للزواج في تونس؟"),
    ("Quel est le prix du litre d'essence sans plomb en Tunisie ?", "ما هو سعر لتر البنزين الخالي من الرصاص في تونس؟"),
    ("Qui a remporté la Coupe du monde de football en 2018 ?", "من فاز بكأس العالم لكرة القدم سنة 2018؟"),
    ("Quelle est la durée du service militaire obligatoire en Tunisie ?", "ما هي مدة الخدمة العسكرية الإجبارية في تونس؟"),
    ("Quelles sont les règles d'attribution du permis de conduire de catégorie B ?", "ما هي شروط الحصول على رخصة السياقة من صنف ب؟"),
    ("Que dit la loi tunisienne sur le droit à l'oubli numérique ?", "ماذا ينص القانون التونسي على الحق في النسيان الرقمي؟"),
]

NUM = re.compile(r"\d+")


def article_text(path, lang, n):
    """Pull article n out of a corpus file (the evidence passage)."""
    t = path.read_text(encoding="utf-8")
    if lang == "ar":
        pat = (r"^\s*الفصل\s*(?:الأول|1\b)" if n == 1 else rf"^\s*الفصل\s*[):]?\s*{n}\s*(?:ـ|-|\)|:|\s)")
        nxt = r"\n\s*الفصل\s*[):]?\s*(?:\d+|الأول)"
    else:
        pat = (r"^\s*(?:Article premier|Art\.\s*1\b|Article\s+1\b)" if n == 1 else rf"^\s*(?:Art\.|Article)\s*{n}\b")
        nxt = r"\n\s*(?:Art\.|Article)\s*(?:\d+|premier)"
    m = re.search(pat, t, re.M)
    if not m:
        return None
    s = t[m.start(): m.start() + 1500]
    e = re.search(nxt, s[5:])
    return re.sub(r"\s+", " ", s[: e.start() + 5] if e else s).strip()


def main():
    out, missing = [], []
    for i, (doc, art, fq, fa, aq, aa, tags) in enumerate(ANSWERABLE, 1):
        for lang, q, a in (("fr", fq, fa), ("ar", aq, aa)):
            folder = "fr" if lang == "fr" else "txt"
            ev = article_text(CORPUS / folder / f"{doc}.txt", lang, art)
            if ev is None:
                missing.append((doc, art, lang))
            out.append({"id": f"q{i:03d}-{lang}", "pair": f"q{i:03d}", "lang": lang, "question": q, "answer": a,
                        "answerable": True, "gold_doc": doc, "gold_articles": [art],
                        "tags": tags.split(), "evidence": ev})
    for j, (fq, aq) in enumerate(UNANSWERABLE, 1):
        for lang, q in (("fr", fq), ("ar", aq)):
            out.append({"id": f"u{j:03d}-{lang}", "pair": f"u{j:03d}", "lang": lang, "question": q,
                        "answer": "I don't know", "answerable": False, "gold_doc": None,
                        "gold_articles": [], "tags": ["unanswerable"], "evidence": None})
    path = ROOT / "data" / "eval" / "qa.jsonl"
    with path.open("w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_ans = sum(r["answerable"] for r in out)
    print(f"{len(out)} questions ({n_ans} answerable, {len(out) - n_ans} unanswerable) -> {path}")
    print("evidence not found:", missing)


if __name__ == "__main__":
    main()
