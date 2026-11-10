from _lib import ROOT
import json
def L(id,title,key,icon,level,story): return {"id":id,"title":title,"kind":"lab","key":key,"icon":icon,"level":level,"story":story}
def W(id,title,topic,icon,level,story): return {"id":id,"title":title,"kind":"words","topic":topic,"icon":icon,"level":level,"story":story}
def S(id,title,icon,level,story): return {"id":id,"title":title,"kind":"soon","icon":icon,"level":level,"story":story}
d={"guide":"Rafi","guideIntro":"Meet Rafi. He just moved from Rajshahi to Dhaka for his first job. Follow his journey, and learn the English he needs at each step.",
"tracks":[
 {"id":"foundations","title":"Sentence foundations","subtitle":"The grammar every sentence needs","icon":"foundation","nodes":[
  L("questions","Questions","lab_questions","help","A2","Day one. Rafi needs to ask where everything is, without sounding rude."),
  L("articles","Articles: a, an, the","lab_articles","article","A2","His manager says: 'You're engineer?' Rafi wants to sound better than that."),
  L("prepositions","Prepositions","lab_prepositions","place","A2","Meetings at 10, on Monday, in Gulshan. Rafi must get the small words right."),
  L("nouns","Nouns and agreement","lab_nouns","inventory","B1","'Can I get some informations?' Rafi learns why his colleague smiled."),
  L("tenses","Tense Lab","tenses","timeline","B1","Rafi tells his team what he did, what he's doing, and what he'll do."),
  W("modals","Modal verbs","modals","gavel","B1","Must, should, might: Rafi learns rules, advice and guesses."),
  L("gerunds","Gerunds and infinitives","lab_gerunds","swap_horiz","B2","'I avoid to be late' or 'I avoid being late'? Rafi finds out."),
  L("passive","Passive voice","lab_passive","published_with_changes","B2","Reports say 'It was decided…'. Rafi learns why."),
  L("relatives","Relative clauses and comparisons","lab_relatives","link","B2","The client who called, the plan that works, the best option.")]},
 {"id":"natural","title":"Natural speech","subtitle":"Sound like a native, not a textbook","icon":"record_voice_over","nodes":[
  W("phrasal","Phrasal verbs","phrasal","directions_run","A2","Colleagues say 'put off', 'figure out', 'catch up'. Rafi wants to follow."),
  W("collocations","Collocations","collocations","join_inner","B1","Make a decision, not do a decision."),
  W("discourse","Fillers and discourse","discourse","forum","B1","Actually, I mean, anyway: the glue of real conversation."),
  W("linking","Linking ideas","linking","account_tree","B1","On top of that, having said that: Rafi connects his points."),
  W("idioms","Idioms","idioms","emoji_objects","B2","'Let's call it a day.' Rafi finally gets the joke.")]},
 {"id":"functions","title":"Communication skills","subtitle":"Do things with English","icon":"handshake","nodes":[
  L("politeness","Politeness and tone","lab_politeness","volunteer_activism","B1","Rafi's 'Send the file' upset someone. Time to learn tone."),
  W("hedging","Softening and hedging","hedging","tune","B1","'I was wondering if…' Rafi sounds confident but kind."),
  L("opinions","Opinions, agreeing, disagreeing","lab_opinions","thumbs_up_down","B2","In his first meeting Rafi disagrees, politely."),
  L("plans","Plans, invitations, offers","lab_plans","event","B1","Team lunch on Friday? Rafi invites and accepts."),
  L("problems","Complaining and solving problems","lab_problems","build","B2","The laptop broke. Rafi calls IT."),
  L("stories","Telling stories","lab_stories","auto_stories","B2","At the team dinner Rafi tells the story of his village."),
  L("negotiate","Persuading and negotiating","lab_negotiate","balance","C1","Rafi's first client wants a discount.")]},
 {"id":"situations","title":"Real situations","subtitle":"Everything together, in real life","icon":"work","nodes":[
  L("email","Email and chat","lab_email","mail","B1","Rafi's inbox is full. He writes clear, modern replies."),
  L("smalltalk","Small talk and introductions","lab_smalltalk","waving_hand","A2","Lift, tea break, a new colleague: Rafi breaks the ice."),
  L("calls","Phone and video calls","lab_calls","call","B1","'Can you hear me? You're on mute.'"),
  L("interview","Job interview","lab_interview","badge","B2","A year later, Rafi interviews for a better job."),
  L("meetings","Meetings and presentations","lab_meetings","co_present","B2","Rafi presents the quarterly results."),
  L("customers","Customers and clients","lab_customers","support_agent","B2","An angry customer calls. Rafi stays calm."),
  L("travel","Travel: airport and hotel","lab_travel","flight","B1","Rafi's first business trip to Singapore."),
  L("daily","Daily life: doctor, bank, shop","lab_daily","storefront","A2","Life in Dhaka: bank account, doctor, rent.")]}]}
(ROOT/"v1"/"data"/"labs.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n")
print("journey ok")
