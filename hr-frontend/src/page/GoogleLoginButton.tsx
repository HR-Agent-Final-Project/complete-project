import { auth, googleProvider } from "../firebase";
import { signInWithPopup } from "firebase/auth";
import axios from "axios";

export default function GoogleLoginButton() {

  const handleGoogleLogin = async () => {
    try {
      // Step 1: Firebase handles Google popup
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      // Step 2: Get Firebase ID token
      const idToken = await user.getIdToken();

      // Step 3: Send to our backend
      const response = await axios.post(
        "http://localhost:8001/api/auth/google/firebase",
        { id_token: idToken }
      );

      // Step 4: Save our JWT tokens
      const { access_token, refresh_token, employee_name } = response.data;
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      alert(`Welcome ${employee_name}!`);
      window.location.href = "/dashboard";

    } catch (error: any) {
      if (error.response?.status === 403) {
        alert("Your Google account is not registered. Contact HR.");
      } else {
        alert("Google login failed. Try again.");
      }
    }
  };

  return (
    <button
      onClick={handleGoogleLogin}
      className="flex items-center gap-3 bg-white border border-gray-300 
                 rounded-lg px-6 py-3 hover:bg-gray-50 transition"
    >
      <img
        src="https://www.google.com/favicon.ico"
        alt="Google"
        className="w-5 h-5"
      />
      <span className="text-gray-700 font-medium">
        Sign in with Google
      </span>
    </button>
  );
}
