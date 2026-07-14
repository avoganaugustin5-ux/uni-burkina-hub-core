/**
 * UTS_ORG_DATA.js — Données centralisées de l'Université Thomas SANKARA
 * Source : Arrêté n°2026/MESRI/SG/UTS + Organigramme officiel UTS
 * À inclure avant tout fichier HTML du projet : <script src="uts_org_data.js"></script>
 */

// ══════════════════════════════════════════════════════════════════════════
// HIÉRARCHIE COMPLÈTE DE L'UTS
// ══════════════════════════════════════════════════════════════════════════
const UTS_ORG = {

  // ── 1. PRÉSIDENCE ──────────────────────────────────────────────────────
  president: {
    id: 'president', label: 'Président de l\'Université', abbrev: 'PRESIDENT',
    branche: 'Présidence', niveau: 1, type: 'individuel',
    icon: '🏛️', couleur: '#C0392B',
    description: 'Coordonne et contrôle l\'ensemble des activités de l\'UTS'
  },

  // ── 2. CABINET ─────────────────────────────────────────────────────────
  ccab: {
    id: 'ccab', label: 'Chef de Cabinet', abbrev: 'CCAB',
    branche: 'Cabinet', parent: 'president', niveau: 2, type: 'individuel',
    icon: '💼', couleur: '#922B21',
    description: 'Dirige le Cabinet du Président'
  },
  cj: {
    id: 'cj', label: 'Conseiller Juridique', abbrev: 'CJ',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'individuel',
    icon: '⚖️', couleur: '#922B21'
  },
  cat: {
    id: 'cat', label: 'Chargés d\'Appui Technique', abbrev: 'CAT',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '🔧', couleur: '#922B21',
    description: 'Deux CAT rattachés au Cabinet'
  },
  protocole: {
    id: 'protocole', label: 'Protocole', abbrev: 'PROTOCOLE',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '🎗️', couleur: '#922B21'
  },
  'sp-cab': {
    id: 'sp-cab', label: 'Secrétariat Particulier du Cabinet', abbrev: 'SP-CAB',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '📋', couleur: '#922B21'
  },
  sc: {
    id: 'sc', label: 'Service de la Communication', abbrev: 'SC',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '📢', couleur: '#922B21'
  },
  ssu: {
    id: 'ssu', label: 'Service de la Sécurité Universitaire', abbrev: 'SSU',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '🔒', couleur: '#922B21'
  },
  ci: {
    id: 'ci', label: 'Contrôle Interne', abbrev: 'CI',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '🔍', couleur: '#922B21'
  },
  ciaq: {
    id: 'ciaq', label: 'Cellule Interne d\'Assurance Qualité', abbrev: 'CIAQ',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'service',
    icon: '✅', couleur: '#922B21'
  },
  prcp: {
    id: 'prcp', label: 'Personne Responsable de la Commande Publique', abbrev: 'PRCP',
    branche: 'Cabinet', parent: 'ccab', niveau: 3, type: 'individuel',
    icon: '📑', couleur: '#922B21'
  },
  smtpi: {
    id: 'smtpi', label: 'Service des Marchés de Travaux et Prestations Intellectuelles', abbrev: 'SMTPI',
    branche: 'Cabinet', parent: 'prcp', niveau: 4, type: 'service',
    icon: '🏗️', couleur: '#922B21'
  },
  smfpc: {
    id: 'smfpc', label: 'Service des Marchés de Fournitures et Prestations Courantes', abbrev: 'SMFPC',
    branche: 'Cabinet', parent: 'prcp', niveau: 4, type: 'service',
    icon: '📦', couleur: '#922B21'
  },
  ssem: {
    id: 'ssem', label: 'Service de Suivi de l\'Exécution des Marchés', abbrev: 'SSEM',
    branche: 'Cabinet', parent: 'prcp', niveau: 4, type: 'service',
    icon: '📊', couleur: '#922B21'
  },

  // ── 3. VICE-PRÉSIDENCE EIP ─────────────────────────────────────────────
  'vp-eip': {
    id: 'vp-eip', label: 'Vice-Président chargé des Enseignements, Innovations Pédagogiques et Professionnalisation', abbrev: 'VP-EIP',
    branche: 'VP-EIP', parent: 'president', niveau: 2, type: 'individuel',
    icon: '🎓', couleur: '#1E8449',
    description: 'Vice-Présidence EIP'
  },
  'sp-vpeip': {
    id: 'sp-vpeip', label: 'Secrétariat Particulier VP-EIP', abbrev: 'SP-EIP',
    branche: 'VP-EIP', parent: 'vp-eip', niveau: 3, type: 'service',
    icon: '📋', couleur: '#1E8449'
  },
  // DSI
  dsi: {
    id: 'dsi', label: 'Direction des Systèmes d\'Information', abbrev: 'DSI',
    branche: 'VP-EIP', parent: 'vp-eip', niveau: 3, type: 'directeur',
    icon: '💻', couleur: '#1E8449'
  },
  seap: {
    id: 'seap', label: 'Service des Études et Applications', abbrev: 'SEAp',
    branche: 'VP-EIP', parent: 'dsi', niveau: 4, type: 'service',
    icon: '🖥️', couleur: '#1E8449'
  },
  srss: {
    id: 'srss', label: 'Service Réseaux, Systèmes et Sécurité', abbrev: 'SRSS',
    branche: 'VP-EIP', parent: 'dsi', niveau: 4, type: 'service',
    icon: '🌐', couleur: '#1E8449'
  },
  ssm: {
    id: 'ssm', label: 'Service Support et Maintenance', abbrev: 'SSM',
    branche: 'VP-EIP', parent: 'dsi', niveau: 4, type: 'service',
    icon: '🔧', couleur: '#1E8449'
  },
  // DEI
  dei: {
    id: 'dei', label: 'Direction des Enseignements et Innovations Pédagogiques', abbrev: 'DEI',
    branche: 'VP-EIP', parent: 'vp-eip', niveau: 3, type: 'directeur',
    icon: '📚', couleur: '#1E8449'
  },
  spfee: {
    id: 'spfee', label: 'Service des Programmes de Formation, des Enseignements et des Examens', abbrev: 'SPFEE',
    branche: 'VP-EIP', parent: 'dei', niveau: 4, type: 'service',
    icon: '📝', couleur: '#1E8449'
  },
  spu: {
    id: 'spu', label: 'Service de la Pédagogie Universitaire', abbrev: 'SPU',
    branche: 'VP-EIP', parent: 'dei', niveau: 4, type: 'service',
    icon: '🎯', couleur: '#1E8449'
  },
  // DPE
  dpe: {
    id: 'dpe', label: 'Direction de la Professionnalisation et de l\'Entrepreneuriat', abbrev: 'DPE',
    branche: 'VP-EIP', parent: 'vp-eip', niveau: 3, type: 'directeur',
    icon: '🚀', couleur: '#1E8449'
  },
  spi: {
    id: 'spi', label: 'Service de la Professionnalisation et de l\'Insertion', abbrev: 'SPI',
    branche: 'VP-EIP', parent: 'dpe', niveau: 4, type: 'service',
    icon: '💼', couleur: '#1E8449'
  },
  scie: {
    id: 'scie', label: 'Service de la Créativité, de l\'Incubation et de l\'Entrepreneuriat', abbrev: 'SCIE',
    branche: 'VP-EIP', parent: 'dpe', niveau: 4, type: 'service',
    icon: '💡', couleur: '#1E8449'
  },
  // DAOI
  daoi: {
    id: 'daoi', label: 'Direction des Affaires Académiques, de l\'Orientation et de l\'Information', abbrev: 'DAOI',
    branche: 'VP-EIP', parent: 'vp-eip', niveau: 3, type: 'directeur',
    icon: '🎓', couleur: '#1E8449'
  },
  siir: {
    id: 'siir', label: 'Service de l\'Information, des Inscriptions et des Réinscriptions', abbrev: 'SIIR',
    branche: 'VP-EIP', parent: 'daoi', niveau: 4, type: 'service',
    icon: '📝', couleur: '#1E8449'
  },
  std: {
    id: 'std', label: 'Service des Titres et Diplômes', abbrev: 'STD',
    branche: 'VP-EIP', parent: 'daoi', niveau: 4, type: 'service',
    icon: '🏆', couleur: '#1E8449'
  },

  // ── 4. VICE-PRÉSIDENCE RCU ─────────────────────────────────────────────
  'vp-rcu': {
    id: 'vp-rcu', label: 'Vice-Président chargé de la Recherche et de la Coopération Universitaire', abbrev: 'VP-RCU',
    branche: 'VP-RCU', parent: 'president', niveau: 2, type: 'individuel',
    icon: '🔬', couleur: '#154360',
    description: 'Vice-Présidence RCU'
  },
  'sp-vprcu': {
    id: 'sp-vprcu', label: 'Secrétariat Particulier VP-RCU', abbrev: 'SP-RCU',
    branche: 'VP-RCU', parent: 'vp-rcu', niveau: 3, type: 'service',
    icon: '📋', couleur: '#154360'
  },
  // DRV
  drv: {
    id: 'drv', label: 'Direction de la Recherche et de la Valorisation', abbrev: 'DRV',
    branche: 'VP-RCU', parent: 'vp-rcu', niveau: 3, type: 'directeur',
    icon: '🔬', couleur: '#154360'
  },
  sar: {
    id: 'sar', label: 'Service d\'Appui à la Recherche', abbrev: 'SAR',
    branche: 'VP-RCU', parent: 'drv', niveau: 4, type: 'service',
    icon: '🧪', couleur: '#154360'
  },
  svrr: {
    id: 'svrr', label: 'Service de la Valorisation des Résultats de la Recherche', abbrev: 'SVRR',
    branche: 'VP-RCU', parent: 'drv', niveau: 4, type: 'service',
    icon: '📈', couleur: '#154360'
  },
  // DCPE
  dcpe: {
    id: 'dcpe', label: 'Direction de la Coopération Universitaire et de la Promotion des Enseignants', abbrev: 'DCPE',
    branche: 'VP-RCU', parent: 'vp-rcu', niveau: 3, type: 'directeur',
    icon: '🤝', couleur: '#154360'
  },
  scu: {
    id: 'scu', label: 'Service de la Coopération Universitaire', abbrev: 'SCU',
    branche: 'VP-RCU', parent: 'dcpe', niveau: 4, type: 'service',
    icon: '🌍', couleur: '#154360'
  },
  'spe-dcpe': {
    id: 'spe-dcpe', label: 'Service de la Promotion des Enseignants', abbrev: 'SPE',
    branche: 'VP-RCU', parent: 'dcpe', niveau: 4, type: 'service',
    icon: '👨‍🏫', couleur: '#154360'
  },
  // DPRUE
  dprue: {
    id: 'dprue', label: 'Direction de la Prospective et des Relations Université-Entreprises', abbrev: 'DPRUE',
    branche: 'VP-RCU', parent: 'vp-rcu', niveau: 3, type: 'directeur',
    icon: '🏢', couleur: '#154360'
  },
  spec: {
    id: 'spec', label: 'Service de la Prospective, des Études et de la Consultation', abbrev: 'SPEC',
    branche: 'VP-RCU', parent: 'dprue', niveau: 4, type: 'service',
    icon: '📊', couleur: '#154360'
  },
  srue: {
    id: 'srue', label: 'Service des Relations Université-Entreprises', abbrev: 'SRUE',
    branche: 'VP-RCU', parent: 'dprue', niveau: 4, type: 'service',
    icon: '🤝', couleur: '#154360'
  },

  // ── 5. SECRÉTARIAT GÉNÉRAL ──────────────────────────────────────────────
  sg: {
    id: 'sg', label: 'Secrétaire Général', abbrev: 'SG',
    branche: 'SG', parent: 'president', niveau: 2, type: 'individuel',
    icon: '📜', couleur: '#7D6608',
    description: 'Secrétariat Général de l\'Université Thomas SANKARA'
  },
  // Services du SG
  'sp-sg': {
    id: 'sp-sg', label: 'Secrétariat Particulier du SG', abbrev: 'SP-SG',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '📋', couleur: '#7D6608', groupe: 'services-sg'
  },
  be: {
    id: 'be', label: 'Bureau d\'Études', abbrev: 'BE',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '📐', couleur: '#7D6608', groupe: 'services-sg'
  },
  scc: {
    id: 'scc', label: 'Service Central du Courrier', abbrev: 'SCC',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '✉️', couleur: '#7D6608', groupe: 'services-sg'
  },
  sr: {
    id: 'sr', label: 'Service de la Reprographie', abbrev: 'SR',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '🖨️', couleur: '#7D6608', groupe: 'services-sg'
  },
  sa: {
    id: 'sa', label: 'Service des Archives', abbrev: 'SA',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '🗄️', couleur: '#7D6608', groupe: 'services-sg'
  },
  ssac: {
    id: 'ssac', label: 'Service des Sports, Arts et Culture', abbrev: 'SSAC',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'service',
    icon: '⚽', couleur: '#7D6608', groupe: 'services-sg'
  },
  // Structures centrales SG — DAF
  daf: {
    id: 'daf', label: 'Direction de l\'Administration des Finances', abbrev: 'DAF',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '💰', couleur: '#7D6608'
  },
  saf: {
    id: 'saf', label: 'Service Administratif et Financier', abbrev: 'SAF',
    branche: 'SG', parent: 'daf', niveau: 4, type: 'service',
    icon: '📒', couleur: '#7D6608'
  },
  scp: {
    id: 'scp', label: 'Service de la Commande Publique', abbrev: 'SCP',
    branche: 'SG', parent: 'daf', niveau: 4, type: 'service',
    icon: '📑', couleur: '#7D6608'
  },
  ra: {
    id: 'ra', label: 'Régie d\'Avance', abbrev: 'RA',
    branche: 'SG', parent: 'daf', niveau: 4, type: 'service',
    icon: '💵', couleur: '#7D6608'
  },
  // DEP
  dep: {
    id: 'dep', label: 'Direction des Études et de la Planification', abbrev: 'DEP',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '📈', couleur: '#7D6608'
  },
  spse: {
    id: 'spse', label: 'Service de la Planification, des Statistiques et de l\'Évaluation', abbrev: 'SPSE',
    branche: 'SG', parent: 'dep', niveau: 4, type: 'service',
    icon: '📊', couleur: '#7D6608'
  },
  ssd: {
    id: 'ssd', label: 'Service du Suivi et de la Documentation', abbrev: 'SSD',
    branche: 'SG', parent: 'dep', niveau: 4, type: 'service',
    icon: '📁', couleur: '#7D6608'
  },
  // DRH
  drh: {
    id: 'drh', label: 'Direction des Ressources Humaines', abbrev: 'DRH',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '👥', couleur: '#7D6608'
  },
  ssgc: {
    id: 'ssgc', label: 'Service de la Solde et de la Gestion des Carrières', abbrev: 'SSGC',
    branche: 'SG', parent: 'drh', niveau: 4, type: 'service',
    icon: '📋', couleur: '#7D6608'
  },
  sgpep: {
    id: 'sgpep', label: 'Service de la Gestion Prévisionnelle des Emplois et des Postes', abbrev: 'SGPEP',
    branche: 'SG', parent: 'drh', niveau: 4, type: 'service',
    icon: '🗂️', couleur: '#7D6608'
  },
  // BCMP
  bcmp: {
    id: 'bcmp', label: 'Bureau Comptable Matières Principal', abbrev: 'BCMP',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '🧾', couleur: '#7D6608'
  },
  smcg: {
    id: 'smcg', label: 'Service de la Matière et des Cessions et Gestion', abbrev: 'SMCG',
    branche: 'SG', parent: 'bcmp', niveau: 4, type: 'service',
    icon: '📦', couleur: '#7D6608'
  },
  saie: {
    id: 'saie', label: 'Service des Affaires Immobilières et de l\'Environnement', abbrev: 'SAIE',
    branche: 'SG', parent: 'bcmp', niveau: 4, type: 'service',
    icon: '🏘️', couleur: '#7D6608'
  },
  // BUC
  buc: {
    id: 'buc', label: 'Bibliothèque Universitaire Centrale', abbrev: 'BUC',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '📚', couleur: '#7D6608'
  },
  sato: {
    id: 'sato', label: 'Service des Acquisitions et du Traitement des Ouvrages', abbrev: 'SATO',
    branche: 'SG', parent: 'buc', niveau: 4, type: 'service',
    icon: '📗', couleur: '#7D6608'
  },
  sd: {
    id: 'sd', label: 'Service de la Documentation', abbrev: 'SD',
    branche: 'SG', parent: 'buc', niveau: 4, type: 'service',
    icon: '📂', couleur: '#7D6608'
  },
  // DPU
  dpu: {
    id: 'dpu', label: 'Direction des Presses Universitaires', abbrev: 'DPU',
    branche: 'SG', parent: 'sg', niveau: 3, type: 'directeur',
    icon: '🖊️', couleur: '#7D6608'
  },
  smc: {
    id: 'smc', label: 'Service de l\'Impression et de la Mise en Page', abbrev: 'SMC',
    branche: 'SG', parent: 'dpu', niveau: 4, type: 'service',
    icon: '🖨️', couleur: '#7D6608'
  },
  se: {
    id: 'se', label: 'Service de l\'Édition', abbrev: 'SE',
    branche: 'SG', parent: 'dpu', niveau: 4, type: 'service',
    icon: '📖', couleur: '#7D6608'
  },

  // ── 6. INSTANCES ────────────────────────────────────────────────────────
  ca: {
    id: 'ca', label: 'Conseil d\'Administration', abbrev: 'CA',
    branche: 'Instances', parent: 'president', niveau: 2, type: 'instance',
    icon: '🏛️', couleur: '#4A235A'
  },
  cs: {
    id: 'cs', label: 'Conseil Scientifique', abbrev: 'CS',
    branche: 'Instances', parent: 'president', niveau: 2, type: 'instance',
    icon: '🔭', couleur: '#4A235A'
  },
  cfvu: {
    id: 'cfvu', label: 'Commission de Formation et de Vie Universitaire', abbrev: 'CFVU',
    branche: 'Instances', parent: 'president', niveau: 2, type: 'instance',
    icon: '📋', couleur: '#4A235A'
  }
};

// ══════════════════════════════════════════════════════════════════════════
// GROUPES POUR L'INSCRIPTION — listes déroulantes organisées
// ══════════════════════════════════════════════════════════════════════════
const UTS_GROUPES_INSCRIPTION = [
  {
    groupe: 'Direction',
    description: 'Présidence et Vice-Présidences',
    roleCode: 'DIRECTION',
    couleur: '#C0392B',
    membres: [
      { id: 'president', label: 'Président de l\'Université' },
      { id: 'vp-eip', label: 'Vice-Président EIP' },
      { id: 'vp-rcu', label: 'Vice-Président RCU' },
      { id: 'sg', label: 'Secrétaire Général' }
    ]
  },
  {
    groupe: 'Cabinet du Président',
    description: 'Members du Cabinet',
    roleCode: 'CABINET',
    couleur: '#922B21',
    membres: [
      { id: 'ccab', label: 'Chef de Cabinet (CCAB)' },
      { id: 'cj', label: 'Conseiller Juridique (CJ)' },
      { id: 'cat', label: 'Chargé d\'Appui Technique (CAT)' },
      { id: 'protocole', label: 'Protocole' },
      { id: 'sp-cab', label: 'Secrétariat Particulier — Cabinet' },
      { id: 'sc', label: 'Service Communication (SC)' },
      { id: 'ssu', label: 'Service Sécurité Universitaire (SSU)' },
      { id: 'ci', label: 'Contrôle Interne (CI)' },
      { id: 'ciaq', label: 'Cellule Assurance Qualité (CIAQ)' },
      { id: 'prcp', label: 'Responsable Commande Publique (PRCP)' },
      { id: 'smtpi', label: 'Service Marchés Travaux (SMTPI)' },
      { id: 'smfpc', label: 'Service Marchés Fournitures (SMFPC)' },
      { id: 'ssem', label: 'Service Suivi Exécution Marchés (SSEM)' }
    ]
  },
  {
    groupe: 'VP-EIP — Direction des Systèmes d\'Information (DSI)',
    description: 'Informatique & Réseaux',
    roleCode: 'EMPLOYE_DSI',
    couleur: '#1E8449',
    membres: [
      { id: 'dsi', label: 'Directeur DSI' },
      { id: 'seap', label: 'Service Études et Applications (SEAp)' },
      { id: 'srss', label: 'Service Réseaux, Systèmes et Sécurité (SRSS)' },
      { id: 'ssm', label: 'Service Support et Maintenance (SSM)' },
      { id: 'sp-vpeip', label: 'Secrétariat Particulier VP-EIP' }
    ]
  },
  {
    groupe: 'VP-EIP — Direction des Enseignements (DEI)',
    description: 'Pédagogie & Programmes',
    roleCode: 'EMPLOYE_DEI',
    couleur: '#1A5276',
    membres: [
      { id: 'dei', label: 'Directeur DEI' },
      { id: 'spfee', label: 'Service Programmes, Formations et Examens (SPFEE)' },
      { id: 'spu', label: 'Service Pédagogie Universitaire (SPU)' }
    ]
  },
  {
    groupe: 'VP-EIP — Direction Professionnalisation (DPE)',
    description: 'Insertion & Entrepreneuriat',
    roleCode: 'EMPLOYE_DPE',
    couleur: '#1A5276',
    membres: [
      { id: 'dpe', label: 'Directeur DPE' },
      { id: 'spi', label: 'Service Professionnalisation et Insertion (SPI)' },
      { id: 'scie', label: 'Service Créativité, Incubation et Entrepreneuriat (SCIE)' }
    ]
  },
  {
    groupe: 'VP-EIP — Direction Affaires Académiques (DAOI)',
    description: 'Orientation & Inscriptions',
    roleCode: 'EMPLOYE_DAOI',
    couleur: '#1A5276',
    membres: [
      { id: 'daoi', label: 'Directeur DAOI' },
      { id: 'siir', label: 'Service Information, Inscriptions et Réinscriptions (SIIR)' },
      { id: 'std', label: 'Service Titres et Diplômes (STD)' }
    ]
  },
  {
    groupe: 'VP-RCU — Direction Recherche et Valorisation (DRV)',
    description: 'Recherche scientifique',
    roleCode: 'EMPLOYE_DRV',
    couleur: '#154360',
    membres: [
      { id: 'drv', label: 'Directeur DRV' },
      { id: 'sar', label: 'Service Appui à la Recherche (SAR)' },
      { id: 'svrr', label: 'Service Valorisation des Résultats (SVRR)' },
      { id: 'sp-vprcu', label: 'Secrétariat Particulier VP-RCU' }
    ]
  },
  {
    groupe: 'VP-RCU — Direction Coopération Universitaire (DCPE)',
    description: 'Coopération & Promotion',
    roleCode: 'EMPLOYE_DCPE',
    couleur: '#154360',
    membres: [
      { id: 'dcpe', label: 'Directeur DCPE' },
      { id: 'scu', label: 'Service Coopération Universitaire (SCU)' },
      { id: 'spe-dcpe', label: 'Service Promotion des Enseignants (SPE)' }
    ]
  },
  {
    groupe: 'VP-RCU — Direction Prospective (DPRUE)',
    description: 'Relations Université-Entreprises',
    roleCode: 'EMPLOYE_DPRUE',
    couleur: '#154360',
    membres: [
      { id: 'dprue', label: 'Directeur DPRUE' },
      { id: 'spec', label: 'Service Prospective, Études et Consultation (SPEC)' },
      { id: 'srue', label: 'Service Relations Université-Entreprises (SRUE)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Services directs',
    description: 'SP, BE, SCC, SR, SA, SSAC',
    roleCode: 'EMPLOYE_SG_SERVICES',
    couleur: '#7D6608',
    membres: [
      { id: 'sp-sg', label: 'Secrétariat Particulier du SG (SP-SG)' },
      { id: 'be', label: 'Bureau d\'Études (BE)' },
      { id: 'scc', label: 'Service Central du Courrier (SCC)' },
      { id: 'sr', label: 'Service de la Reprographie (SR)' },
      { id: 'sa', label: 'Service des Archives (SA)' },
      { id: 'ssac', label: 'Service Sports, Arts et Culture (SSAC)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Administration & Finances (DAF)',
    description: 'Gestion financière',
    roleCode: 'EMPLOYE_DAF',
    couleur: '#6E2F0E',
    membres: [
      { id: 'daf', label: 'Directeur DAF' },
      { id: 'saf', label: 'Service Administratif et Financier (SAF)' },
      { id: 'scp', label: 'Service Commande Publique (SCP)' },
      { id: 'ra', label: 'Régie d\'Avance (RA)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Études et Planification (DEP)',
    description: 'Planification & Statistiques',
    roleCode: 'EMPLOYE_DEP',
    couleur: '#6E2F0E',
    membres: [
      { id: 'dep', label: 'Directeur DEP' },
      { id: 'spse', label: 'Service Planification, Statistiques et Évaluation (SPSE)' },
      { id: 'ssd', label: 'Service Suivi et Documentation (SSD)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Ressources Humaines (DRH)',
    description: 'Personnel & Carrières',
    roleCode: 'EMPLOYE_DRH',
    couleur: '#6E2F0E',
    membres: [
      { id: 'drh', label: 'Directeur DRH' },
      { id: 'ssgc', label: 'Service Solde et Gestion des Carrières (SSGC)' },
      { id: 'sgpep', label: 'Service Gestion Prévisionnelle des Emplois (SGPEP)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Comptabilité Matières (BCMP)',
    description: 'Patrimoine & Matières',
    roleCode: 'EMPLOYE_BCMP',
    couleur: '#6E2F0E',
    membres: [
      { id: 'bcmp', label: 'Bureau Comptable Matières Principal (BCMP)' },
      { id: 'smcg', label: 'Service Matière, Cessions et Gestion (SMCG)' },
      { id: 'saie', label: 'Service Affaires Immobilières et Environnement (SAIE)' }
    ]
  },
  {
    groupe: 'Secrétariat Général — Bibliothèque (BUC)',
    description: 'Documentation & Édition',
    roleCode: 'EMPLOYE_BUC',
    couleur: '#6E2F0E',
    membres: [
      { id: 'buc', label: 'Directeur BUC' },
      { id: 'sato', label: 'Service Acquisitions et Traitement des Ouvrages (SATO)' },
      { id: 'sd', label: 'Service de la Documentation (SD)' },
      { id: 'dpu', label: 'Directeur Presses Universitaires (DPU)' },
      { id: 'smc', label: 'Service Impression et Mise en Page (SMC)' },
      { id: 'se', label: 'Service de l\'Édition (SE)' }
    ]
  }
];

// ══════════════════════════════════════════════════════════════════════════
// DASHBOARDS — Mapping rôle → type de dashboard
// ══════════════════════════════════════════════════════════════════════════
const UTS_DASHBOARD_TYPES = {
  // Rôles individuels uniques
  'superadmin':   { template: 'superadmin',   label: 'Super Administrateur', icon: '⚙️' },
  'president':    { template: 'president',     label: 'Président',            icon: '🏛️' },
  'vp-eip':       { template: 'vp',            label: 'Vice-Président EIP',   icon: '🎓' },
  'vp-rcu':       { template: 'vp',            label: 'Vice-Président RCU',   icon: '🔬' },
  'sg':           { template: 'sg',            label: 'Secrétaire Général',   icon: '📜' },
  'ccab':         { template: 'cadre-cabinet', label: 'Chef de Cabinet',      icon: '💼' },
  'cj':           { template: 'cadre-cabinet', label: 'Conseiller Juridique', icon: '⚖️' },
  'prcp':         { template: 'cadre-cabinet', label: 'PRCP',                 icon: '📑' },
  // Directeurs — dashboard commun mais adapté par direction
  'dsi':  { template: 'directeur', label: 'Directeur DSI',   icon: '💻' },
  'dei':  { template: 'directeur', label: 'Directeur DEI',   icon: '📚' },
  'dpe':  { template: 'directeur', label: 'Directeur DPE',   icon: '🚀' },
  'daoi': { template: 'directeur', label: 'Directeur DAOI',  icon: '🎓' },
  'drv':  { template: 'directeur', label: 'Directeur DRV',   icon: '🔬' },
  'dcpe': { template: 'directeur', label: 'Directeur DCPE',  icon: '🤝' },
  'dprue':{ template: 'directeur', label: 'Directeur DPRUE', icon: '🏢' },
  'daf':  { template: 'directeur', label: 'Directeur DAF',   icon: '💰' },
  'dep':  { template: 'directeur', label: 'Directeur DEP',   icon: '📈' },
  'drh':  { template: 'directeur', label: 'Directeur DRH',   icon: '👥' },
  'bcmp': { template: 'directeur', label: 'Directeur BCMP',  icon: '🧾' },
  'buc':  { template: 'directeur', label: 'Directeur BUC',   icon: '📚' },
  'dpu':  { template: 'directeur', label: 'Directeur DPU',   icon: '🖊️' },
  // Services — dashboard commun "employé de service"
  'employe': { template: 'employe-service', label: 'Employé de Service', icon: '👔' },
  // Acteurs académiques
  'enseignant':     { template: 'enseignant',     label: 'Enseignant(e)',     icon: '👨‍🏫' },
  'chef_dept':      { template: 'chef-dept',      label: 'Chef de Département', icon: '🏫' },
  'etudiant':       { template: 'etudiant',       label: 'Étudiant(e)',       icon: '🎓' },
  'delegue':        { template: 'delegue',        label: 'Délégué(e)',        icon: '🗣️' },
  'sous_admin':     { template: 'sous-admin',     label: 'Sous-Administrateur', icon: '🔧' }
};

// ══════════════════════════════════════════════════════════════════════════
// CHAÎNE HIÉRARCHIQUE — pour le routage documentaire
// Retourne le chemin par défaut depuis un poste vers le sommet
// ══════════════════════════════════════════════════════════════════════════
function getChainHierarchique(postId) {
  const chain = [];
  let current = UTS_ORG[postId];
  while (current) {
    chain.unshift(current.id);
    current = current.parent ? UTS_ORG[current.parent] : null;
  }
  return chain;
}

// Retourne tous les acteurs pouvant recevoir un document (pour la sélection du chemin)
function getAllActeurs() {
  return Object.values(UTS_ORG).map(a => ({
    id: a.id,
    label: `${a.abbrev} — ${a.label}`,
    branche: a.branche,
    niveau: a.niveau,
    type: a.type
  })).sort((a, b) => a.niveau - b.niveau || a.branche.localeCompare(b.branche));
}

// Retourne les acteurs d'une branche donnée
function getActeursByBranche(branche) {
  return Object.values(UTS_ORG).filter(a => a.branche === branche);
}

// Trouve le poste par son ID
function getPoste(id) {
  return UTS_ORG[id] || null;
}
