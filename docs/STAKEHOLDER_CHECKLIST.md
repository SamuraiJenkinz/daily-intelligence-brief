# MDInsights Production Launch Approval Checklist

**Project:** MDInsights - Daily Intelligence Brief System
**Prepared by:** Kevin Taylor, Colleague Technology Services
**Date prepared:** February 8, 2026
**Stakeholder approval date:** ___________________
**Approved by:** ___________________

---

## 1. Sample Brief Review

**Instructions:** Review generated sample brief for brand compliance and content quality.

### Brand Compliance
- [ ] **Visual design matches Marsh brand guidelines**
  - Marsh blue (#00263e) header gradient present
  - Segoe UI font family used throughout
  - Color palette matches Marsh standards
  - Professional, clean layout

- [ ] **Attribution and compliance markings present**
  - "Kevin Taylor, Colleague Technology Services" attribution visible
  - "CONFIDENTIAL" marking displayed
  - Marsh company name appears correctly
  - Report date/time stamp present

- [ ] **Template structure matches prototype**
  - Browser template uses tabs for role navigation
  - Executive summary sections display correctly
  - Article cards render with all fields (title, source, excerpt, chips)
  - Analytics sections (heatmap, entity tracker, market pulse) function properly

### Content Quality
- [ ] **Article classification accuracy**
  - Articles assigned to correct roles (Brokers, Leadership, Compliance, Underwriting)
  - Relevance scores are reasonable
  - Key themes identified accurately
  - Entity extraction (companies, locations) is correct

- [ ] **Executive summaries are substantive**
  - Summaries capture key insights from articles
  - Language is professional and clear
  - "What to Watch" items are actionable
  - No hallucinations or fabricated content

- [ ] **Aggregated analytics add value**
  - Sector heatmap shows meaningful patterns
  - Entity tracker highlights important companies/locations
  - Market pulse indicators are relevant
  - Cross-cutting themes make sense

---

## 2. Email Delivery Review

**Instructions:** Send test emails to yourself and verify rendering across email clients.

### Per-Role Email Delivery
- [ ] **Brokers role email sent successfully**
  - Email received in inbox
  - Subject line clear and professional
  - From address is correct sender
  - CC/BCC recipients configured (if applicable)

- [ ] **Leadership role email sent successfully**
  - Email received in inbox
  - Content appropriate for executive audience
  - Executive summary sections prominent

- [ ] **Compliance role email sent successfully**
  - Email received in inbox
  - Regulatory content prioritized
  - Compliance-specific themes highlighted

- [ ] **Underwriting role email sent successfully**
  - Email received in inbox
  - Risk-related content prioritized
  - Underwriting themes highlighted

### Email Rendering Quality
- [ ] **Outlook rendering (desktop and web)**
  - Header gradient displays correctly
  - Colors match Marsh brand
  - Tables render properly
  - No layout breaks or misalignments

- [ ] **Gmail rendering (web and mobile)**
  - Header appears correctly
  - Content is readable on mobile
  - Links work properly
  - No CSS conflicts

- [ ] **Links and interactivity**
  - "View in browser" link works
  - Article source links open correctly
  - Footer attribution is visible
  - Confidentiality notice displays

---

## 3. Production Readiness

**Instructions:** Verify automated systems are configured and operational.

### Task Scheduler Configuration
- [ ] **Daily pipeline task registered**
  - Task: "MDInsights Daily Pipeline"
  - Scheduled for 06:00 daily
  - Runs with correct user account
  - Batch script path correct

- [ ] **Backup task registered**
  - Task: "MDInsights Daily Pipeline - Backup"
  - Scheduled for 07:00 daily
  - Azure Blob Storage configured (if applicable)
  - Retention policy set (30 days)

- [ ] **Drift monitoring task registered**
  - Task: "MDInsights Daily Pipeline - Drift Check"
  - Scheduled for Monday 08:00
  - Admin alert email configured

- [ ] **Health monitoring task registered**
  - Task: "MDInsights Daily Pipeline - Monitor"
  - Scheduled for 09:00 daily
  - Monitors source health and alerts

### Monitoring and Alerting
- [ ] **Admin email alerts configured**
  - ADMIN_EMAIL environment variable set
  - Test failure alert received successfully
  - Alert emails are actionable

- [ ] **Logging system operational**
  - JSON logs writing to logs/mdinsights.log
  - Log rotation configured (30 days)
  - Logs contain structured data for debugging

- [ ] **Production validation script passes**
  - Run: `python scripts/validate_production_ready.py`
  - All required checks pass
  - Environment variables configured
  - Database has enabled sources

### Documentation and Handoff
- [ ] **Administrator guide reviewed**
  - docs/ADMINISTRATOR_GUIDE.md complete
  - All operational workflows documented
  - Troubleshooting section clear

- [ ] **Deployment guide reviewed**
  - docs/DEPLOYMENT_GUIDE.md complete
  - Azure AD app registration steps documented
  - Environment variable setup clear

- [ ] **Source management documented**
  - How to enable/disable sources
  - How to add new Apify sources
  - How to configure RSS feeds

---

## 4. Approval Decision

### Production Go-Live Approval

**Is MDInsights ready for production deployment?**

- [ ] **YES** - All criteria met, approved for production launch
- [ ] **YES, with conditions** - Approved with minor conditions (list below)
- [ ] **NO** - Not ready, requires additional work (list below)

**Conditions or required changes (if applicable):**

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

**Approver signature:** ________________________________
**Date:** ___________________
**Title:** ___________________

---

## 5. Post-Launch Plan

### First Week
- [ ] Monitor daily pipeline execution logs
- [ ] Verify email delivery to all recipients
- [ ] Collect initial user feedback from recipients
- [ ] Address any rendering issues reported
- [ ] Confirm backup job runs successfully

### First Month
- [ ] Review classification accuracy with stakeholders
- [ ] Assess article volume and source performance
- [ ] Evaluate executive summary quality
- [ ] Adjust source configurations if needed
- [ ] Plan any feature enhancements based on feedback

### Ongoing
- [ ] Weekly review of error logs and alerts
- [ ] Monthly review of classification drift metrics
- [ ] Quarterly review of source health and performance
- [ ] Bi-annual review of Azure AD app credentials (renewal before expiry)
- [ ] Annual review of system architecture and scaling needs

---

## Notes

Use this space for additional comments, observations, or feedback:

_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---

**Document version:** 1.0
**Last updated:** February 8, 2026
**Contact:** Kevin Taylor, Colleague Technology Services
