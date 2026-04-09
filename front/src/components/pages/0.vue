<template>
  <div class="consent-page">
    <!-- Header -->
    <div class="page-header">
      <h2 class="header-title">Research Participant Consent Form</h2>
      <p class="header-subtitle">Please read this information carefully before proceeding</p>
    </div>

    <!-- Content -->
    <div class="content-container">
      <div class="consent-content prose prose-slate max-w-none">
        <div class="project-info">
          <h3>Project Title: Information Dissemination in Electronic Financial Markets</h3>

          <div class="info-grid">
            <div class="info-item">
              <div>
                <strong>Institution:</strong>
                <span>Royal Holloway, University of London -- Department of Economics</span>
              </div>
            </div>

            <div class="info-item">
              <div>
                <strong>Researchers:</strong>
                <span
                  >Prof. Alessio Sancetta, Prof. Francesco Feri, Prof. Michael Naef, Dr. Wenbin Wu,
                  Dr. Mariol Jonuzaj</span
                >
              </div>
            </div>

            <div class="info-item">
              <div>
                <strong>Funding Body:</strong>
                <span>The Leverhulme Trust</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-sections">
          <section class="content-section">
            <h4>Introduction</h4>
            <p>
              Royal Holloway, University of London supports the practise of protecting human
              participants in research. This form provides you with important information about
              taking part in this study. Your participation in this study is entirely voluntary, and
              you have the right to withdraw at any time during the experimental session without
              penalty or negative consequences. If you choose to withdraw during the experimental
              session, any data collected from you will be deleted and not included in the final
              analysis. However, you will not be able to withdraw your consent after the study is
              completed, and the payment has been issued.
            </p>
          </section>

          <section class="content-section">
            <h4>Summary</h4>
            <p>
              The purpose of this study is to investigate the interaction between human and machines
              (AI agents) in electronic financial markets. In this study, we will ask you to
              participate in various experimental financial markets where you will be able to make
              decisions regarding buying or selling a virtual financial asset (not a real asset).
              This study will take approximately <strong>30 minutes</strong> to complete. Taking
              part in this study is a great opportunity to learn how electronic financial markets
              operate, and you will also have the chance to earn financial profits depending on your
              performance.
            </p>
          </section>

          <section class="content-section">
            <h4>Ethical Approval</h4>
            <p>
              This study has received ethics approval from Royal Holloway, University of London's
              Research Ethics Committee, with the approval ID of <strong>713</strong>.
            </p>
          </section>

          <section class="content-section">
            <h4>Data Collection</h4>
            <p>
              During this study, we will collect data from you only related to your buy or sell
              decision orders. At the end of the study, you will be asked to complete a short survey
              about your overall experience with our platform. Additionally, the Prolific platform
              will provide some basic demographic characteristics such as age, gender and education.
              All data will be anonymized and labelled using only your Unique Prolific ID.
            </p>
          </section>

          <section class="content-section">
            <h4>Data Protection</h4>
            <p>This research commits to abide by the Data Protection Act (2018).</p>
          </section>

          <section class="content-section">
            <h4>General Data Protection Regulation Statement</h4>
            <div class="gdpr-content">
              <p>
                Important General Data Protection Regulation information (GDPR). Royal Holloway,
                University of London is the sponsor for this study and is based in the UK. We will
                be using information from you in order to undertake this study and will act as the
                data controller for this study. This means that we are responsible for looking after
                your information and using it properly. Any data you provide during the completion
                of the study will be stored securely on hosted on servers within the European
                Economic Area'. Royal Holloway is designated as a public authority and in accordance
                with the Royal Holloway and Bedford New College Act 1985 and the Statutes which
                govern the College, we conduct research for the public benefit and in the public
                interest.
              </p>

              <p>
                Royal Holloway has put in place appropriate technical and organisational security
                measures to prevent your personal data from being accidentally lost, used or
                accessed in any unauthorised way or altered or disclosed. Royal Holloway has also
                put in place procedures to deal with any suspected personal data security breach and
                will notify you and any applicable regulator of a suspected breach where legally
                required to do so.
              </p>

              <p>
                To safeguard your rights, we will use the minimum personally-identifiable
                information possible (i.e., the email address you provide us). The lead researcher
                will keep your contact details confidential and will use this information only as
                required (i.e., to provide a summary of the study results if requested and/or for
                the prize draw).
              </p>

              <p>
                You can find out more about your rights under the GDPR and Data Protection Act 2018
                by visiting
                <a
                  href="https://www.royalholloway.ac.uk/about-us/more/governance-and-strategy/data-protection/"
                  target="_blank"
                  class="external-link"
                  >https://www.royalholloway.ac.uk/about-us/more/governance-and-strategy/data-protection/</a
                >
                and if you wish to exercise your rights, please contact
                <a href="mailto:dataprotection@royalholloway.ac.uk" class="external-link"
                  >dataprotection@royalholloway.ac.uk</a
                >
              </p>
            </div>
          </section>

          <section class="content-section">
            <h4>Compensation</h4>
            <p>
              For your time and effort, you will receive compensation through the Prolific platform
              payment. You will receive a participation fee of <strong>£5 GBP</strong>, and
              additional compensation will be provided based on your performance. This is subject to
              completing the entire study and submitting the completion code displayed at the end of
              the study to the prolific platform.
            </p>
          </section>

          <section class="content-section">
            <h4>Contact Information</h4>
            <p>
              If you have any question, concerns, or feedback related to this study, please feel
              free to contact us through the Prolific message box.
            </p>
          </section>

          <section class="content-section">
            <h4>Statement of Consent</h4>
            <p><strong>I confirm that:</strong></p>
            <ul class="consent-list">
              <li>I have read and understood the information provided in this consent form.</li>
              <li>
                I have had the opportunity to ask questions and have received satisfactory answers.
              </li>
              <li>
                I voluntarily agree to participate in the study "Information Dissemination in
                Electronic Financial Markets"
              </li>
              <li>
                I understand that I can withdraw from the study at any time without penalty or
                negative consequences.
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>

    <!-- Consent checkbox and button -->
    <div class="consent-footer">
      <!-- Lab identity confirmation -->
      <div v-if="participantLabel" class="identity-confirm">
        You are participant <strong>{{ participantLabel }}</strong>. If this is not correct, please contact the researcher.
      </div>

      <div class="checkbox-container">
        <input
          id="consent-checkbox"
          v-model="consentGiven"
          @change="updateConsent"
          type="checkbox"
          class="consent-checkbox"
        />
        <label for="consent-checkbox" class="checkbox-label">
          <div class="checkbox-indicator">
            <span v-if="consentGiven" class="check-mark">&#10003;</span>
          </div>
          <span>I consent to participate in this research study</span>
        </label>
      </div>

      <button
        @click="submitConsent"
        :disabled="!consentGiven"
        class="consent-btn"
        :class="{ disabled: !consentGiven }"
      >
        <span v-if="!consentGiven">Please review and consent above</span>
        <span v-else>Continue to Study</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineEmits } from 'vue'
import { useRouter } from 'vue-router'
import { useTraderStore } from '@/store/app'
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'
import axios from '@/api/axios'

const router = useRouter()
const traderStore = useTraderStore()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const consentGiven = ref(false)

const participantLabel = computed(() => {
  const user = authStore.user
  if (!user) return null
  if (user.isLab) {
    // Extract token from trader ID: HUMAN_LAB_T1_P1 → T1_P1
    const traderId = authStore.traderId || ''
    const match = traderId.match(/LAB_(.+)$/)
    return match ? match[1] : traderId
  }
  if (user.isProlific) {
    return user.prolificData?.PROLIFIC_PID || 'Prolific Participant'
  }
  return null
})

const emit = defineEmits(['update:canProgress'])

const updateConsent = (event) => {
  const value = event.target.checked
  emit('update:canProgress', value)
}

const submitConsent = async () => {
  if (!consentGiven.value) return

  try {
    const traderId = traderStore.traderId
    const marketId = traderStore.marketId
    const traderUuid = traderStore.traderId

    console.log('Trader info:', { traderId, marketId, traderUuid })
    console.log('Auth store state:', {
      isAuthenticated: authStore.isAuthenticated,
      user: authStore.user,
      prolificId: authStore.prolificId,
    })

    const isProlificUser = !!authStore.prolificId

    let userId = ''
    let userType = ''

    if (isProlificUser) {
      userId = authStore.prolificId
      userType = 'prolific'
    } else if (authStore.user?.email) {
      const email = authStore.user.email
      userId = email.split('@')[0]
      userType = 'google'
    } else if (authStore.user?.uid) {
      userId = authStore.user.uid
      userType = 'google'
    }

    console.log('User identification:', { userId, userType, isProlificUser })

    try {
      const requestData = {
        trader_id: traderId,
        user_id: userId || '',
        user_type: userType || '',
        prolific_id: authStore.prolificId || '',
        consent_given: true,
      }

      console.log('Trying debug endpoint first:', requestData)
      const debugResponse = await axios.post('/consent/debug', requestData)
      console.log('Debug endpoint response:', debugResponse.data)

      console.log('Sending consent data to backend:', requestData)
      const response = await axios.post('/consent/save', requestData)
      console.log(`Consent data saved for user:`, response.data)
    } catch (submitError) {
      console.error('Error submitting consent:', submitError)
      if (submitError.response) {
        console.error('Response data:', submitError.response.data)
        console.error('Response status:', submitError.response.status)
        console.error('Response headers:', submitError.response.headers)
      }
    }

    // Use NavigationService to go to next step
    await NavigationService.nextOnboardingStep()
  } catch (error) {
    console.error('Error handling consent:', error)
    if (error.response) {
      console.error('Response data:', error.response.data)
      console.error('Response status:', error.response.status)
      console.error('Response headers:', error.response.headers)
    } else if (error.request) {
      console.error('Request error:', error.request)
    } else {
      console.error('Error message:', error.message)
    }
  }
}
</script>

<style scoped>
.consent-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.header-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 0.5rem 0;
  line-height: 1.2;
}

.header-subtitle {
  color: var(--color-text-secondary);
  font-size: 1rem;
  margin: 0;
}

.content-container {
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  padding: 2rem;
  border: var(--border-width) solid var(--color-border);
  margin-bottom: 2rem;
}

.project-info {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid var(--color-border);
}

.project-info h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 1.5rem;
  text-align: center;
}

.info-grid {
  display: grid;
  gap: 1rem;
}

.info-item {
  padding: 1rem;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.info-item strong {
  display: block;
  color: var(--color-text-primary);
  margin-bottom: 0.25rem;
}

.info-item span {
  color: var(--color-text-secondary);
}

.content-sections {
  display: grid;
  gap: 1.5rem;
}

.content-section {
  padding: 1.5rem;
  border-radius: var(--radius-md);
  border: var(--border-width) solid var(--color-border);
  background: var(--color-bg-elevated);
}

.content-section h4 {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 1rem 0;
}

.content-section p {
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 0.75rem 0;
}

.content-section p:last-child {
  margin-bottom: 0;
}

.gdpr-content {
  background: var(--color-bg-subtle);
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.consent-list {
  margin: 1rem 0;
  padding-left: 0;
  list-style: none;
}

.consent-list li {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: var(--color-bg-subtle);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
}

.consent-list li::before {
  content: '\2713';
  color: var(--color-success);
  font-weight: bold;
  flex-shrink: 0;
}

.external-link {
  color: var(--color-primary);
  text-decoration: underline;
}

.consent-footer {
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  padding: 2rem;
  border: var(--border-width) solid var(--color-border);
  text-align: center;
}

.identity-confirm {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  background: var(--color-bg-elevated);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-family);
}

.checkbox-container {
  margin-bottom: 2rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  cursor: pointer;
  font-weight: 500;
  color: var(--color-text-primary);
}

.consent-checkbox {
  display: none;
}

.checkbox-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
}

.consent-checkbox:checked + .checkbox-label .checkbox-indicator {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.check-mark {
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: bold;
}

.consent-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 2rem;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  min-width: 200px;
}

.consent-btn.disabled {
  background: var(--color-text-muted);
  color: var(--color-bg-elevated);
  cursor: not-allowed;
}

/* Responsive design */
@media (max-width: 768px) {
  .consent-page {
    padding: 0 0.5rem;
  }

  .content-container {
    padding: 1.5rem;
  }

  .content-section {
    padding: 1rem;
  }

  .checkbox-label {
    text-align: left;
  }

  .consent-btn {
    width: 100%;
  }
}

/* Typography improvements */
.prose {
  color: var(--color-text-secondary);
  max-width: none;
}

.prose p {
  margin-bottom: 1rem;
  line-height: 1.7;
}

.prose strong {
  color: var(--color-text-primary);
  font-weight: 600;
}

.prose h3 {
  color: var(--color-text-primary);
  font-weight: 700;
  margin-bottom: 1rem;
}

.prose h4 {
  color: var(--color-text-primary);
  font-weight: 600;
  margin-bottom: 0.75rem;
}
</style>
