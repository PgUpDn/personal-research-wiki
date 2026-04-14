---
title: "Real-Time Digital Twin - Deep Dive | Industrial Engineering Livestream Series"
source: "https://www.youtube.com/watch?v=PKmm7bv38Tk"
author:
  - "[[NVIDIA Developer]]"
published: 2025-11-26
created: 2026-04-14
description: "Join our Real-Time Digital Twin (RTDT) Deep Dive livestream to learn about how to build RTDT’s using Omniverse APIs , kit-CAE extension and NVIDIA PhysicsNeMo. This session includes live walk-through"
tags:
  - "clippings"
---
![](https://www.youtube.com/watch?v=PKmm7bv38Tk)

Join our Real-Time Digital Twin (RTDT) Deep Dive livestream to learn about how to build RTDT’s using Omniverse APIs , kit-CAE extension and NVIDIA PhysicsNeMo. This session includes live walk-through of the code base and examples for automotive, aerospace and data-center design.  
  
We’ll cover, step by step:  
  
A live demonstration of building and using the NVIDIA Omniverse kit-CAE extension for industrial engineering problems, integrating data from CFD, structural analysis, and more.  
  
Walkthroughs of the different data importers and extended USD schema for handling common CAE file formats like CGNS, EnSight, VTK, and NumPy.  
  
Guidance on accessing open-source resources, documentation, and using the sample scripts, with live Q&A throughout.

## Transcript

**1:05** · Hi and welcome back to the NVIDIA industrial engineering live stream.

**1:10** · Today we're going to be talking about real time digital twins. If this is the first time of watching this, welcome.

**1:17** · We've actually had two episodes uh before we did a bit of a recap on what is Nvidia doing in this space and last week we talked about AI physics building AI surrogate models that can do this real-time prediction. So we decided today building on that theme we're going to talk about how you can integrate some of those previous technologies into a digital twin. We're going to be talking about omniverse APIs. We're going to be talking about kits and how you can do it. And um I thought I'll bring along two of my friends uh who know a lot more about this than I do, Abby and Ukash, who actually have built this stuff themselves working with partners and customers and I thought they would be the best people to talk about it. So uh if we can bring them on screen, maybe they can um introduce themselves and then we can uh start to get in. This is going to be like a deep dive session. So this code will be shown be warned this isn't just slides. Um, so, uh, yeah, maybe Abby, do you want to quickly introduce yourself for people?

**2:16** · Sure.

**2:16** · Hi everyone. My name is Abigail.

**2:18** · I'm a technical marketing engineer. Um, I've been doing my whole career in CFD and computational stuff and I'm excited to be here to talk about this.

**2:28** · Cool.

**2:29** · Hey everyone, thanks for the welcome Neil. Uh, I'm with Kar and I'm a dev, a scientific visualization devtech here at NVIDIA and my focus is primary scientific data analysis and visualization.

**2:40** · And Abby has two very cute dogs, which I really hope will come up in the \[laughter\] background because last time we were preparing this, they were like fighting in the background. And so I yeah, I kind of hope that actually \[laughter\] comes up. Um, okay. So, we don't have that much time. We're going to try and keep these condensed. So, I think maybe a good starting point is what actually are we talking about when we talk about real-time digital twins?

**3:03** · Maybe Abby, I think you've got a couple of slides and a nice video to to illustrate this.

**3:08** · Yeah, sure. So we can go ahead and take a look at um a slide. I know this is not death by PowerPoint. It's just one slide to get started. So if we can show the architectural diagram. Yeah. So what we're doing is we were putting together blueprints or how to work with some of the technologies that we have at NVIDIA.

**3:28** · And I think Neil talked about the real-time wind tunnel last time or in the other episodes. Um but this is a very basic architecture of how it's created. There's a few um pillars of this blueprint. Um one is physics nemo which I think was covered last time and another one is kit CE and how we visualize large data that's often found in CFD simulations and CAE simulations.

**3:56** · how we visualize that in a in real time um and and in like beautiful environments that are that are accurate for um like how they're actually tested.

**4:07** · So that I think that's what we're going to go over today is Kit CE um and how that integrates and enables these blueprints. Um so we've done a few now like you said Neil, we did um a a car and then most recently we did a um an airplane. So, if we can go to that to show the video of this um blueprint for this airplane. And this was really fun to work on. Um we all worked on it as a team together and we showed it off at GTCDC and also at Supercomputing. So what we did here is we took um an airplane and we changed or we allowed the users to modify the flaps and the slats configuration as well as the angle of attack um in real time and get results in real time and v visualize it in real time. And this is all part of the um the the blueprint that we put together.

**5:04** · Yeah.

**5:04** · And this was something that I guess was building on you know a year ago I think we showed like the road car which is what I showed in the past few episodes and then SME was saying ah but you know how could this be done to other things and so you know we showed this to show how you can do it for an aircraft and we talked in the last episode I guess more on the surrogate modeling you know how do we train a model using prior simulation data to be able to give this real time but one of the questions that I certainly get a lot is well how could I do this I'm a developer uh you know I work at an ISV or a startup or or a developer and other code and I want to have this sort of capability to visualize a wind turbine, a bike, a data center, a plane and so I guess today is about getting into the the code of the magic behind this taking back the curtain I suppose. Um and yeah it was fun wasn't it? It was a bit stressful, but it was Yeah. \[laughter\] Yeah. It was It was great. And and it's, you know, it's really impressive. I think sometimes people see this and they just see, oh, wow, that's beautiful. But what's really impressive, I think, is the the accuracy behind it. You know, the technologies that we're hooking together. And one of the ways we do that is with Kit CE. and kit um is basically a sample of extensions and APIs just brought together to work with large data sets um efficiently. So so I mean as you can imagine in simulations like this it could be very very heavy um and here we're you know real-time inferencing so um it's pretty impressive to be able to work with these data and like visualize it in real time. Um can I just interrupt for one second? I just pressed the wrong button. So somebody else's comment came up. This is the comment I meant to show. Um you said is this I think they mean is it like a pre-solved or is it from physics team?

**6:57** · This is actually the real time inference from the AI model. So this this is not a movie. This is not a trick. This is actually the real time. And if you look really closely there's a like a black banner at the top saying waiting for inference then inference happening. Uh and that's that's the real time. So sorry to interrupt. Just want to answer that question.

**7:17** · No, that's an important that's important thing to show. Um so yeah, I think today we'll just get into a little bit of how kit CE enables working with this data. Um it there's like a few big pillars that come together for kit CIE. Like I said, it's a sample for developers to um see how they could work with their large CE data. Um but it it involves USD schemas um some algorithms flow index and warp and also um yeah just data delegates and I think Ukar you're going to get into that a little bit.

**7:58** · Yeah.

**7:58** · Yeah. Before we do that though, can we go back to the movie for one sec?

**8:01** · I just want to highlight what Quitsier brings into that equation there. Uh, so if you look at the video Yeah.

**8:14** · Come on, Zach. Show the video.

**8:16** · \[laughter\] Bad network connection, I guess.

**8:20** · Anyways, everyone saw the video. So, in the video, you saw some graphical elements on the side, right? The toolbarss and the buttons. All of that is the web client, right? That's a web client that's written in React. But the rendering all the thing that's happening behind it that the airplane model the visualization the flow all of that is what is coming from kits. So yeah so all that rendering stuff is coming from kitsier. Uh what kits is it's a omniverse based sample application. So the key word here is sample right. It is not a product. It's not a thing that you you you can buy off the shelf or any such thing. It's a s it's a example of how you can build this on your own and it is based on what's called kit SDK.

**9:01** · I'm sorry I'm just dropping tons of names here but that's that's the that's the game right so uh so the kit SDK as the name suggests is another SDK right it's a software development kit so it it gives you a rendering engine it gives you bunch of different extensions that you can put together bring together in your application or write your own so kit is a sample that is based on the kit SDK that is geared towards processing scientific data sets and we're talking of simulation results we're talking of inference results So that is what kitsier is. Now with that in mind, now I'm going to share my screen and now we're going to start looking into the code. I'm sorry about that, but I was told that's what I should do.

**9:42** · Yes.

**9:42** · \[laughter\] So blame Neil for that.

**9:48** · So if we can have the git repo link uh on the thing here. So there's a this is all open source, right? have access to kits on GitHub. So, anyone can just go clone it. Uh once you clone it, it'll take a little while. It downloads some data files for testing and stuff. They're not too huge, but uh once all of that is done, there are two steps to build. Uh and step A is repo schema.

**10:16** · This builds the USD schemas and we'll dig into that a little bit. uh but essentially these are the schema extensions that we've developed that tell uh that let us describe data in USD and once that is done you can build the application by doing this repo build so not too crazy this will download all the dependencies that it needs and it will quickly build and then your application is ready to launch so uh those of who who have worked with omniverse in the past or USD applications in the past anytime you're thinking of bringing your data into the Omniverse ecosystem, you're thinking of exporting it to USD, right? You are you do your streamlines, you do your contours, and then you export the geometry, you export the mesh, you export the lines. Uh well, if you're doing that, it's not going to be very helpful or it's not going to be really the turnaround time is going to be slow when it comes to inferencing and live simulation, right? That is just not a workable solution. So, so what we want to do with KCIE is is there another way of looking at this problem, right?

**11:16** · instead of exporting data to USD can I describe my data in USD and let the application bring the data in that way and that is what this application is trying to uh what we're trying to explore in Kier so before I talk too much let me just launch the application and let's give a quick demo and then we can dig into the weeds so to launch I'm going to mistype so I'm just going to go so this this command to launch it should take a second to launch launch it does its thing and this is the application right uh is a standard omniverse kid-based application uh so I was debating whether to show the data the stage that we used for the airplane demo or something basic in the end I decided to go with something simpler just so that we can focus into the USD and see what's happening there directly uh so let's open a standard CGNS data set everyone is familiar with CGNS uh especially those in the CFD world so everyone's aware of CGNS So I'm going to open a standard sample data set that comes that's just available online called the static mixer right as soon as I import it. Nothing happens but this thing shows up in the stage. Uh this is if for those who you're familiar with CGS this is literally how the data is laid out in the CGS file right it's a hierarchical structure which tells you about different element blocks and different field arrays. Uh what we are doing here is the import process is just reading the metadata from the CGNS file and building the stage. Uh this only reads metadata. That's a keyword, right? So this this is a tiny data set, a few megabytes, but we can easily load gigabytes of data in instantaneously because all we're reading is the metadata to build the stage. So no more converting data to anything. All you do is scan the metadata and set up the stage. Once I have the stage, uh we'll go into the details of the schema in a second here. But this the schema kind of tells me all the information I need to know about this element block like the B1 P3 element block. It's connectivity stored in this field. It it's it's of type this this is the element and so on and so forth. All the stuff that we've gleaned from the metadata. Uh now let's do some visualization operations on it.

**13:25** · And all of these are shown under this menu called CE algorithms. One of the basic ones is bounding box. Right? a quick bounding box. That is my bounding box of data set.

**13:36** · Can I just ask there was a question um popped up maybe as you're doing this one was is there a preferred format like VTK, CGNS, right? So there is none. You can add support for any format that you want. In the example, we have included several.

**13:52** · We have included several VTK formats. So VTUs uh VTKs, VTUs, VTS's, VTI, we have included ends sites for surfaces. We have included CGNS for volumes and surfaces and and there are a few others that I'm forgetting off the top of my head. But essentially, you can bring any format that you want and follow the model that we have we have demonstrated in the sample.

**14:16** · Yeah. Okay.

**14:18** · Right. Because it's it's just teaching you're just teaching how like where to find the data. So you're not converting it right right?

**14:26** · Yeah.

**14:28** · So once we have this is a bounding box nothing look too crazy just next step from that do external faces right just apply the external faces algorithm and here's our external faces. The nice thing KCA also shows is that how to bring in external libraries to do your work. So in this case we're not computing the external faces ourselves using VTK to do that. If you have your own custom library that knows how to work with your data, you can bring that in into this framework to get the work done. Uh so if I want to color apply color, standard things here, nothing too crazy. Uh I can select which field I want to color by.

**15:03** · Let's say temperature and it'll color by that.

**15:07** · I'm I'm going to ask you another qu because this is the whole point of this is for people to ask questions. So I I apologize for to interrupt but please please. So this was a question see as three different themes playing VTK and streaming. Uh when should a user prefer one over the other?

**15:25** · So they are not mutually exclusive to another. Uh and you'll see once you start looking at the USD schemas uh the abstractions that we've built how to get the data and how to access data make this irrelevant of where the data is coming from. It could be live be coming from so wire it could be on the desk or it could be on the cloud or whatever it does not matter right the application simply just uh works with just this collection of arbitrary arrays that has been given from somewhere else and I think that is where that's where the USD model of looking at data shines which is very exciting in my mind does that answer the question Neil well maybe actually just to take a step back what is USD how would you explain USD open USD the just 30 second \[laughter\] description.

**16:09** · Oh my goodness.

**16:12** · Okay. Does anyone else want to take a stab at that? \[laughter\] So, so USDA is a So, it's a way of describing a 3D scene, right? It came from the uh graphics world, right? It came from Pixar if I'm not mistaken. I'm going to miscode things here, so please don't hold me for that. But right. Yeah. Okay. So it it was essentially made for developing these large rendering scenes where you have different actors, different animations and different scenes set up. Right. So there's the notion of a stage. It's your stage. Uh and so the nice thing with USDs besides the whole rendering stuff is it also gives you a nice way of describing state right describing state and defining connections between states.

**16:57** · And that is why applications like uh kit uh have adopted that as the way of talking about the stage right the standardized way and there are several applications that support USD as well right you can export to USD uh there are blenders and there many others which can let you build stages using USD or scenes using USD so if all of this entire ecosystem starts talking in USD then they can work with each other and they can interrupt so that is my way summary of USD Yeah. And I'll also Yeah. Yes. But I'll also add that it's very good for multiple teams to work together in one location because there's this idea of layers. Like somebody that's interested in thermal could be working in thermal simulations and somebody else in flow and somebody else in something else and just all combining in one like central location. And so I feel like that's um that kind of I I didn't realize that when I first started working with them and then when I did realize like it's really powerful to have a central location and a central like scene that we can all communicate in.

**18:04** · Yeah.

**18:04** · It's like VRML on steroids, right?

**18:06** · Like it's it's like you had your standard graph scene descriptions that were used like decades ago and suddenly now and this is literally on steroids because it's insanely powerful. Like when I came to USD, I always thought it's just VRML. It's another exporting format, but it's not. All the composability that Abigail was talking about is what really gives it the leg up and differentiates it from all these other technologies. Uh yeah.

**18:32** · So bes people always want to do that. Uh let's do a nice little unit sphere. I'm going to transform this to make it a little small if I can type. And let's go back to our P3 block again. And sorry about the menu changes real quick.

**19:01** · I'm going to select seam lines. And we specify which field to color by. I'm going to start using shortcuts now for the sake of time. temperature which what are the seed points sphere and what's my velocity X Y and Z and there are my stream lines and again all of this is happening within the application like in in this case you're seeing streamlines that are generated using VTK so it's the data goes to VTK we process it and it's coming back but there are within like I said in sample right so there are examples of doing different things in different ways so we have examples of how to do it using warp warp which is another Nvidia technology which allows you to write Python code that gets compiled that can then run on GPUs or parallel CPUs just like transparently and you can write kernels using that and we have examples in Kier a talk about that. Uh any questions before we look at the stage? Uh Abby Neil, do you think?

**20:17** · Yeah, I think it'd be good to get into the even more deep.

**20:23** · So let me point where things are in the code, right? So if you look at once you check out the repo, all of the code that we talk about is under source. In extensions, we have all these different extensions. So there are extensions for adding support for importing VTK files, adding importing inside files, importing CGNS files. Uh and there are uh there are these other extensions for adding support for different things, right? So in this case it adds support for VTK. So if you open avtk file, this is this is this is where the code is to tell teach the application of how to understand VTK data models. Same with CGNS sits.

**20:59** · Uh so all the code sits here. uh if you are looking let's look at the stage first. So if I had saved the stage that we just created out in in an ASKI format, this is what it looked like, right? So you have a collection of nested prims. And in here you'll see it's directly referring to the CGNS file. There's no it's there's no exported data. It's just lightweight stuff here. Nothing heavy. I'm directly referencing the CGNS file on disk. And let's go down to our Sorry to interrupt. Uh but this I guess we probably should have mentioned this before, but this is probably a good one. So you're talking about like BTK, you're talking about she says they're saying is there a physics extension in Omniverse kit? How do I integrate the library into Kit? I guess there's several answers to that, but yeah. So the R the the RTD demo source code has the extension to extend KCA extensions to add support for talking to an inference server. Uh does that explain does that answer the question?

**22:02** · Yeah, it's like I would say it's like hooks, right? So, so kitsier has the hooks to say like there's the physics nemo data and grab it and pull it in.

**22:11** · So, so this is actually a good point because so if you look at the scheme the stage here, so here is the data set B1 B3 that we were working on, right? So in this case, here's the API schema that tells me this is a CGNS data set. So far so good. But where are the arrays coming from? they point to these prims which are called these field array prims.

**22:31** · Right? So in this case it says it's a CGNS field array. So I know when I'm looking for this field array I'm going to open a CGNS file and look at the in this path. And this is what we call a data delegate. And there's an extension that adds a data delegate for CGNS. Now there's nothing that says this has to come from this file, right? I can easily add another data delegate which is my inference server data delegate. At which point when someone asks me for this array, I'm going to talk to the inference server and get that array. So that is the abstraction that kits offers which then suddenly makes it seamless to talk to inference backends or live simulations or or anything else.

**23:07** · Uh another question is there an extension available for the more modern VTU VTP format or are these through VTK extensions?

**23:16** · So VTU is indeed uh supported already. a VTP it hasn't been added just because we didn't have a use case but if you look at the code and that's where uh like it's it's a it's it's a sample right it doesn't do everything it shows you how to do a few things so that you can then continue the story the way you want it so yes it's fairly straightforward to add support for VTFK PTP VT is already supported great so so going back to the schemas so where are these schemas defined uh If you look at the code, they're all everything is defined under this subdirectory called USD schema. And the schema definitions themselves also look like USD. Uh so here's a schema for this is defining the base data set. This is defining what a field array is. Uh here's a definition for numpy field array. Let's look at the HDFI one. Right? So for HDF1, it's an extension of the basic field array, but it also has an attribute called HDFI path. So it's going to tell me if I want to read a where do I get this field from, right? Uh so I know we're running kind of getting close to the time. So I do want to show one more thing. So we're talking mostly CFD here, right? Even with the uh uh even with the RT the the blueprints we're talking CFD. But there this this this thing is applicable beyond CFD, right? So one of our friends uh Andrew Hobbes uh has this data set where he's running EDM uh simulations which are particle based simulations and this is like 45 gigs of data I believe uh and it's HDFI based oh I need to import file import there 45 gigs of data but like again same same things it loads the metadata in it'll create the stage.

**25:10** · And now look at this. This is where I want to show the beauty of USD, right?

**25:14** · So in this case, this position is coming from this HDF5 array at this path. If I just scroll the time, you see that it changes. It's it's telling me for this next time step, this is where you're going to fetch the array from. I'm not too sure if it's visible, but for time step 55, it's reading it from 55.H5 and the path is also different. \[snorts\] So now I can just glyph this quickly. So if I cliff pick this particle shape there we go and this is 45 gigs almost instantaneous doesn't take because we're only the nice thing with USD is it can tell me what to read and then I can only read just that and that that's expressed very nicely uh within the USD itself.

**26:04** · So I there's a question that came up and I think this is a really good one to to answer that is the target kit for the end user integrate into their individual or for companies and I would say it's more the second one you know most of our focus actually is on uh ISVS startups and and some people who are co-developers to integrate it um it as you the sort of the point of going into the code here is whilst you may see when we build a demo Mo, it looks like a enduser application. In reality, that is just a sample to to show you the art of the possible where in reality you're seeing it's essentially a um uh a bunch of a of APIs and and and samples that show you how a developer could integrate this. But mo probably most of our time is spent working with you know software companies who are trying to integrate this into their platform so that you as an end customer can have this within it.

**27:03** · So um yeah I mean that's probably the yeah that is exactly right and that's why like when people ask divide doesn't it support VTP again our goal is to not it's not a product right the goal is to not do everything it shows you how you could bring in anything right we just demonstrate it with a few samples so that we cover the spectrum uh but then people can take it from there so I I wanted to ask Abby like how people can get started on some of this stuff but I just thought can we show that video before because you sort of teased that swirling uh that's probably not the right way of calling it twirling thing official \[laughter\] that that's a cool video.

**27:43** · Yeah.

**27:43** · So, so it's it's a really small step from where we already were in Kitier. Now all you need to do is set up the camera, set up the lights, set up the rest of the stage and voila. So this is again Andrew's handiwork there. So thanks to him.

**27:56** · Very nice. So Abby, yeah. how I mean you know when you started and and now what what's your advice for people who who have seen this shown on the screen now but want to learn how to do it themselves where they're in a software company they're a developer you know yeah how what sort of links and places would you suggest? Yeah, I've put together a collection if we can just go ahead and show that um for some additional resources. But I think a good a good point is that you know we're asking about like how how do um the the how does kit work with physics nemo and stuff like that. And that's really why we built these blueprints so that you can go and you can download these full blueprints that are an example of how to work with them. So can we can we show that slide Zach of um the links of next steps um where we can go oh yeah \[clears throat\] I think it's yeah there so yeah the next step so like you're saying Neil Kit CE is available on GitHub anyone can download it physics Nemo is available on GitHub um we do have some sample architectures that were built on kit so it just shows how to work with kitc or physics nemo or other API and extensions really customuilt for what you're wanting to do. We have a list of um blueprints that use these, but we also have some self-paced learning that's really great that walks you through step by step. Um you know, you go from Physics Nemo and Aeronim to Inkit CE to visualizing. So that self-paced learning is really great. And also we have this um blog that explains it in a little more detail.

**29:43** · Cool. Well, I want to thank you, Gosh, Abby. I know we could have gone on for hours, you know, to get into this and maybe we'll we'll come back and do another one. Uh it' be good if people can leave comments um or or feedback on what they want to see. But I guess this was hopefully to peel back the curtain a little bit, see the sort of uh way that kitsier works. Um, as as Abby said, if you go to these links, you'll be able to do some selfpaced learning yourself and um and hope you can build your own application. Um, and probably the the easiest one if you want to do it is to go to that buildinvidia.com the um the blueprint that is probably the quickest in that it's already built everything together, but you can go one step further if you want to really customize it and bring in your own stuff by going obviously to the kit itself. So yeah, thank you Abby. Really appreciate it. And thank you everybody for listening in. We'll have another episode in in a couple of weeks. Uh for those in the US, hope you have a nice uh Thanksgiving um week. And for everyone else in the world, just have a nice week. So thanks everybody.

**30:49** · Thank you.

**30:50** · Thank you.