import { useState } from "react";
import { useNavigate } from "react-router-dom";
import BackgroundSlider from "../Background/BackgroundSlider";
import { registerUser } from "../../services/api";
import "./Auth.css";

function Signup() {

  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async () => {

    if (!name || !email || !registrationNumber || !password) {
      setError("Please fill all required fields, including registration number");
      return;
    }

    try {

      setLoading(true);
      setError("");

      await registerUser({
        name: name,
        email: email,
        registration_number: registrationNumber,
        password: password
      });

      alert("Account created successfully!");

      navigate("/login");

    } catch (err) {

      setError(
        err.response?.data?.error || "Registration failed"
      );

    } finally {
      setLoading(false);
    }

  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSignup();
    }
  };

  return (
    <>
      <BackgroundSlider />
      <div className="auth-shell">
        <div className="auth-box">
          <h2 className="auth-title">Create Account</h2>
          <p className="auth-subtitle">Join the student support portal</p>

          {error && <p className="error">{error}</p>}

          <input
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={handleKeyPress}
          />

          <input
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={handleKeyPress}
          />

          <label className="auth-field-label" htmlFor="registration-number">
            Registration Number <span className="required-star">*</span>
          </label>
          <input
            id="registration-number"
            placeholder="Registration Number"
            value={registrationNumber}
            onChange={(e) => setRegistrationNumber(e.target.value)}
            onKeyDown={handleKeyPress}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={handleKeyPress}
          />

          <button onClick={handleSignup} disabled={loading}>
            {loading ? "Creating..." : "Sign Up"}
          </button>

          <p className="auth-switch">
            Already have an account?{" "}
            <button type="button" className="auth-link" onClick={() => navigate("/login")}>
              Login
            </button>
          </p>
        </div>
      </div>
    </>
  );
}

export default Signup;
