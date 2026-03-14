import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAuNqjyzvgubSX1rm_BunIAOyaczHmLSGY",
  authDomain: "ai-hr-manager-ff305.firebaseapp.com",
  projectId: "ai-hr-manager-ff305",
  storageBucket: "ai-hr-manager-ff305.firebasestorage.app",
  messagingSenderId: "29875931569",
  appId: "1:29875931569:web:14a1e02e72c01a2caa5590",
  measurementId: "G-WESCXVW8F9"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();