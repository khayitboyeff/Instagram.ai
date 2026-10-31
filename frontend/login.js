const form=document.getElementById("loginForm");
const password=document.getElementById("password");
const error=document.getElementById("loginError");
const toggle=document.getElementById("togglePassword");

toggle.addEventListener("click",()=>{
  const visible=password.type==="password";
  password.type=visible?"text":"password";
  toggle.setAttribute("aria-label",visible?"Parolni yashirish":"Parolni ko‘rsatish");
  toggle.title=visible?"Parolni yashirish":"Parolni ko‘rsatish";
});
form.addEventListener("submit",async(e)=>{
  e.preventDefault();
  const button=form.querySelector("button[type=submit]");
  const label=button.querySelector(".auth-submit-label");
  button.disabled=true;button.classList.add("is-loading");label.textContent="Tekshirilmoqda...";error.hidden=true;
  try{
    const r=await fetch(window.INSTA_API_BASE+"/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:password.value})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||"Kirish amalga oshmadi. Qayta urinib ko‘ring.");
    sessionStorage.setItem("ias_access_token",d.access_token);location.href="/";
  }catch(err){error.textContent=err.message;error.hidden=false;}
  finally{button.disabled=false;button.classList.remove("is-loading");label.textContent="Kirish";}
});