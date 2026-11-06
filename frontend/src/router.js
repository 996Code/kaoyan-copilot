import { createRouter, createWebHashHistory } from 'vue-router'
import { getToken } from './api'
import LoginView from './views/LoginView.vue'
import HomeView from './views/HomeView.vue'
import PapersView from './views/PapersView.vue'
import ExamView from './views/ExamView.vue'
import ReportView from './views/ReportView.vue'
import PracticeView from './views/PracticeView.vue'
import WrongbookView from './views/WrongbookView.vue'
import ReviewView from './views/ReviewView.vue'
import VocabView from './views/VocabView.vue'
import AdminView from './views/AdminView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/', component: HomeView },
    { path: '/papers/:subject', component: PapersView, props: true },
    { path: '/exam/:paperId', component: ExamView, props: true },
    { path: '/report/:examId', component: ReportView, props: true },
    { path: '/practice', component: PracticeView },
    { path: '/wrongbook', component: WrongbookView },
    { path: '/review', component: ReviewView },
    { path: '/vocab', component: VocabView },
    { path: '/admin', component: AdminView },
  ],
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !getToken()) return '/login'
})
