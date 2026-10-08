import json,re,collections
GT={
14:'''Sign Up Create your account Full Name Email Password Confirm Password Sign Up Already have an account? Login''',
15:'''Login Welcome back! Please login to your account. Email or Username Password Forgot password? Login Don't have an account? Sign up''',
16:'''Sketch2Code Home Features How It Works About Contact Login Turn Your Sketches into Real Code Sketch2Code is an AI-powered platform that converts your hand-drawn wireframes into clean, editable React code instantly. Get Started Our Features Everything you need in one place. Easy to Use Clean and simple interface for better experience. Accurate Component Detection Detects UI components from sketches using AI. Editable Code Output Generate clean React code with live preview. 2026 Sketch2Code. All rights reserved.''',
17:'''StudentPortal Home Students Departments Reports About Admin Student Details Search students... Add Student No. Name Roll No. Department Email Phone Action 1 Aarav Mehta S001 Computer Science aarav@example.com 9876543210 2 Diya Nair S002 Information Technology diya@example.com 9876543211 3 Rohan Kumar S003 Electronics rohan@example.com 9876543212 4 Sneha Thomas S004 Mechanical sneha@example.com 9876543213 5 Vikram Singh S005 Civil vikram@example.com 9876543214 1 2 3''',
18:'''StudentPortal Dashboard Students Projects Tasks Reports Admin Dashboard Welcome back, Admin! 120 Total Students 5 Departments 12 Ongoing Projects 30 Completed Projects 8 Reports Generated 4 Upcoming Deadlines''',
19:'''Sketch2Code Home Features About Contact Logout Sivani sivani@gmail.com Settings Profile Notifications Security Settings Update your preferences. Name Sivani R Email sivani@gmail.com Theme Light Enable email notifications Make my profile public Save Changes'''
}
def tok(s):
 s=s.lower().replace('_',' ').replace('’',"'")
 return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?(?:@[a-z0-9.]+)?",s)
def score(pred,truth):
 a=collections.Counter(tok(pred)); b=collections.Counter(tok(truth)); match=sum((a&b).values()); return len(list(tok(truth))),len(list(tok(pred))),match, round(match/sum(b.values())*100,2),round(match/sum(a.values())*100,2)
for n,truth in GT.items():
 d=json.load(open(f'/mnt/data/pipeline-trace ({n}).json'))
 raw=' '.join(x['text'] for x in d['raw_ocr_texts']); final=' '.join(x['text'] for x in d['ocr_texts']); print(n,'raw',score(raw,truth),'mapped',score(final,truth))
