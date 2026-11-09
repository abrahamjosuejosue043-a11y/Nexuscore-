<!DOCTYPE html>
<html lang="pt-BR" class="h-full bg-slate-950 text-slate-100">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Core - Sala de Conferência de Agentes IA</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: {
                            50: '#f0f5ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            900: '#1e3a8a',
                        },
                        nexus: {
                            dark: '#0B0F17',
                            card: '#131B2E',
                            accent: '#6366F1',
                            cyan: '#06B6D4',
                            emerald: '#10B981',
                            amber: '#F59E0B',
                            purple: '#A855F7'
                        }
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                    },
                    animation: {
                        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0.0, 0.6, 1) infinite',
                        'glow': 'glow 2s ease-in-out infinite alternate',
                        'sound-wave': 'soundWave 1.2s ease-in-out infinite alternate',
                    },
                    keyframes: {
                        glow: {
                            '0%': { boxShadow: '0 0 5px rgba(99, 102, 241, 0.4)' },
                            '100%': { boxShadow: '0 0 20px rgba(99, 102, 241, 0.9), 0 0 30px rgba(6, 182, 212, 0.6)' }
                        },
                        soundWave: {
                            '0%': { height: '4px' },
                            '100%': { height: '24px' }
                        }
                    }
                }
            }
        }
    </script>

    <style>
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0B0F17;
        }
        ::-webkit-scrollbar-thumb {
            background: #1E293B;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }

        .avatar-glow-atlas {
            box-shadow: 0 0 25px -2px rgba(59, 130, 246, 0.6);
        }
        .avatar-glow-lyra {
            box-shadow: 0 0 25px -2px rgba(168, 85, 247, 0.6);
        }
        .avatar-glow-chronos {
            box-shadow: 0 0 25px -2px rgba(245, 158, 11, 0.6);
        }
        .avatar-glow-user {
            box-shadow: 0 0 25px -2px rgba(16, 185, 129, 0.6);
        }
    </style>
</head>
<body class="h-full flex flex-col font-sans bg-nexus-dark text-slate-100 overflow-hidden select-none">

    <!-- Top Header Navigation -->
    <header class="h-14 px-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md flex items-center justify-between z-20">
        <div class="flex items-center space-x-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-cyan-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <i class="fa-solid fa-microchip text-white text-lg"></i>
            </div>
            <div>
                <div class="flex items-center space-x-2">
                    <h1 class="font-bold text-sm tracking-wide text-white">NEXUS CORE</h1>
                    <span class="bg-indigo-500/20 text-indigo-400 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-indigo-500/30">AI ROOM</span>
                </div>
                <p class="text-xs text-slate-400 font-medium flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Sessão Multimodal Ativa &bull; <span id="clockDisplay">00:00</span>
                </p>
            </div>
        </div>

        <div class="flex items-center space-x-2">
            <!-- Room Code / Status Badge -->
            <div class="hidden sm:flex items-center gap-2 bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-1.5 text-xs text-slate-300">
                <i class="fa-solid fa-lock text-emerald-400 text-xs"></i>
                <span class="font-mono text-slate-200">nexus-live-7hdh</span>
                <button onclick="copyRoomLink()" title="Copiar Link" class="hover:text-white transition">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>

            <button id="toggleSidebarBtn" onclick="toggleSidebar()" class="relative p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition border border-slate-700/50">
                <i class="fa-solid fa-comments"></i>
                <span id="unreadBadge" class="hidden absolute -top-1 -right-1 w-3 h-3 bg-indigo-500 rounded-full border-2 border-slate-900"></span>
            </button>
        </div>
    </header>

    <!-- Main Content Area: Video Grid + Sidebar -->
    <div class="flex-1 flex overflow-hidden relative">

        <!-- Grid Video Layout (Google Meet Style) -->
        <main class="flex-1 p-3 md:p-6 flex flex-col justify-between overflow-y-auto relative bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
            
            <!-- Participant Video Cards Grid -->
            <div id="videoGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4 w-full max-w-6xl mx-auto my-auto transition-all duration-300">
                
                <!-- CARD 1: Atlas (Arquiteto de Software) -->
                <div id="card-atlas" class="relative group aspect-video bg-nexus-card rounded-2xl border-2 border-slate-800/80 overflow-hidden shadow-xl transition-all duration-300 flex flex-col justify-between p-4">
                    <!-- Status Ring when speaking -->
                    <div class="speaking-border absolute inset-0 border-4 border-cyan-400 rounded-2xl opacity-0 pointer-events-none transition-opacity duration-300 z-10"></div>
                    
                    <!-- Top Info Tag -->
                    <div class="flex justify-between items-start z-10">
                        <div class="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-cyan-500/30">
                            <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
                            <span class="text-xs font-semibold text-cyan-200">Atlas</span>
                            <span class="text-[10px] text-slate-400 font-normal">| Arquiteto</span>
                        </div>
                        <div class="bg-slate-900/70 p-1.5 rounded-lg text-slate-300 text-xs flex items-center gap-1.5">
                            <i class="fa-solid fa-brain text-cyan-400"></i>
                            <span class="text-[10px] text-slate-400">GPT-4o</span>
                        </div>
                    </div>

                    <!-- Avatar Center -->
                    <div class="absolute inset-0 flex items-center justify-center">
                        <div class="relative">
                            <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 p-1 avatar-glow-atlas transition-transform duration-300 group-hover:scale-105 flex items-center justify-center">
                                <div class="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden">
                                    <i class="fa-solid fa-robot text-4xl text-cyan-400"></i>
                                </div>
                            </div>
                            <!-- Audio Wave Visualizer overlay -->
                            <div id="wave-atlas" class="hidden absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-end justify-center gap-1 h-6 px-3 py-1 bg-slate-900/90 rounded-full border border-cyan-500/40">
                                <span class="w-1 bg-cyan-400 rounded-full animate-sound-wave" style="animation-delay: 0.1s"></span>
                                <span class="w-1 bg-cyan-400 rounded-full animate-sound-wave" style="animation-delay: 0.3s"></span>
                                <span class="w-1 bg-cyan-400 rounded-full animate-sound-wave" style="animation-delay: 0.2s"></span>
                                <span class="w-1 bg-cyan-400 rounded-full animate-sound-wave" style="animation-delay: 0.4s"></span>
                            </div>
                        </div>
                    </div>

                    <!-- Bottom Bar -->
                    <div class="flex justify-between items-end z-10">
                        <span class="text-xs font-medium text-slate-300 bg-slate-900/60 px-2.5 py-1 rounded-md backdrop-blur-sm">
                            <i class="fa-solid fa-microchip text-cyan-400 mr-1.5"></i>Atlas (IA)
                        </span>
                        <div class="flex gap-1.5">
                            <button onclick="triggerAgentSpeech('atlas')" class="px-2.5 py-1 bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 rounded-md text-xs border border-cyan-500/40 transition">
                                <i class="fa-solid fa-play mr-1"></i>Falar
                            </button>
                        </div>
                    </div>
                </div>

                <!-- CARD 2: Lyra (Estrategista de Marketing) -->
                <div id="card-lyra" class="relative group aspect-video bg-nexus-card rounded-2xl border-2 border-slate-800/80 overflow-hidden shadow-xl transition-all duration-300 flex flex-col justify-between p-4">
                    <!-- Status Ring when speaking -->
                    <div class="speaking-border absolute inset-0 border-4 border-purple-400 rounded-2xl opacity-0 pointer-events-none transition-opacity duration-300 z-10"></div>
                    
                    <div class="flex justify-between items-start z-10">
                        <div class="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-purple-500/30">
                            <span class="w-2 h-2 rounded-full bg-purple-400"></span>
                            <span class="text-xs font-semibold text-purple-200">Lyra</span>
                            <span class="text-[10px] text-slate-400 font-normal">| Marketing</span>
                        </div>
                        <div class="bg-slate-900/70 p-1.5 rounded-lg text-slate-300 text-xs flex items-center gap-1.5">
                            <i class="fa-solid fa-bolt text-purple-400"></i>
                            <span class="text-[10px] text-slate-400">Claude 3.5</span>
                        </div>
                    </div>

                    <div class="absolute inset-0 flex items-center justify-center">
                        <div class="relative">
                            <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-purple-600 via-pink-600 to-rose-500 p-1 avatar-glow-lyra transition-transform duration-300 group-hover:scale-105 flex items-center justify-center">
                                <div class="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden">
                                    <i class="fa-solid fa-chart-line text-4xl text-purple-400"></i>
                                </div>
                            </div>
                            <div id="wave-lyra" class="hidden absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-end justify-center gap-1 h-6 px-3 py-1 bg-slate-900/90 rounded-full border border-purple-500/40">
                                <span class="w-1 bg-purple-400 rounded-full animate-sound-wave" style="animation-delay: 0.2s"></span>
                                <span class="w-1 bg-purple-400 rounded-full animate-sound-wave" style="animation-delay: 0.1s"></span>
                                <span class="w-1 bg-purple-400 rounded-full animate-sound-wave" style="animation-delay: 0.4s"></span>
                                <span class="w-1 bg-purple-400 rounded-full animate-sound-wave" style="animation-delay: 0.3s"></span>
                            </div>
                        </div>
                    </div>

                    <div class="flex justify-between items-end z-10">
                        <span class="text-xs font-medium text-slate-300 bg-slate-900/60 px-2.5 py-1 rounded-md backdrop-blur-sm">
                            <i class="fa-solid fa-wand-magic-sparkles text-purple-400 mr-1.5"></i>Lyra (IA)
                        </span>
                        <div class="flex gap-1.5">
                            <button onclick="triggerAgentSpeech('lyra')" class="px-2.5 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 rounded-md text-xs border border-purple-500/40 transition">
                                <i class="fa-solid fa-play mr-1"></i>Falar
                            </button>
                        </div>
                    </div>
                </div>

                <!-- CARD 3: Chronos (Gestor de Riscos) -->
                <div id="card-chronos" class="relative group aspect-video bg-nexus-card rounded-2xl border-2 border-slate-800/80 overflow-hidden shadow-xl transition-all duration-300 flex flex-col justify-between p-4">
                    <!-- Status Ring when speaking -->
                    <div class="speaking-border absolute inset-0 border-4 border-amber-400 rounded-2xl opacity-0 pointer-events-none transition-opacity duration-300 z-10"></div>
                    
                    <div class="flex justify-between items-start z-10">
                        <div class="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-amber-500/30">
                            <span class="w-2 h-2 rounded-full bg-amber-400"></span>
                            <span class="text-xs font-semibold text-amber-200">Chronos</span>
                            <span class="text-[10px] text-slate-400 font-normal">| Finanças</span>
                        </div>
                        <div class="bg-slate-900/70 p-1.5 rounded-lg text-slate-300 text-xs flex items-center gap-1.5">
                            <i class="fa-solid fa-shield-halved text-amber-400"></i>
                            <span class="text-[10px] text-slate-400">Gemini 1.5 Pro</span>
                        </div>
                    </div>

                    <div class="absolute inset-0 flex items-center justify-center">
                        <div class="relative">
                            <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-amber-600 via-orange-600 to-yellow-500 p-1 avatar-glow-chronos transition-transform duration-300 group-hover:scale-105 flex items-center justify-center">
                                <div class="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden">
                                    <i class="fa-solid fa-coins text-4xl text-amber-400"></i>
                                </div>
                            </div>
                            <div id="wave-chronos" class="hidden absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-end justify-center gap-1 h-6 px-3 py-1 bg-slate-900/90 rounded-full border border-amber-500/40">
                                <span class="w-1 bg-amber-400 rounded-full animate-sound-wave" style="animation-delay: 0.3s"></span>
                                <span class="w-1 bg-amber-400 rounded-full animate-sound-wave" style="animation-delay: 0.1s"></span>
                                <span class="w-1 bg-amber-400 rounded-full animate-sound-wave" style="animation-delay: 0.2s"></span>
                                <span class="w-1 bg-amber-400 rounded-full animate-sound-wave" style="animation-delay: 0.4s"></span>
                            </div>
                        </div>
                    </div>

                    <div class="flex justify-between items-end z-10">
                        <span class="text-xs font-medium text-slate-300 bg-slate-900/60 px-2.5 py-1 rounded-md backdrop-blur-sm">
                            <i class="fa-solid fa-calculator text-amber-400 mr-1.5"></i>Chronos (IA)
                        </span>
                        <div class="flex gap-1.5">
                            <button onclick="triggerAgentSpeech('chronos')" class="px-2.5 py-1 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 rounded-md text-xs border border-amber-500/40 transition">
                                <i class="fa-solid fa-play mr-1"></i>Falar
                            </button>
                        </div>
                    </div>
                </div>

                <!-- CARD 4: VOCÊ (Usuário) -->
                <div id="card-user" class="relative group aspect-video bg-nexus-card rounded-2xl border-2 border-slate-800/80 overflow-hidden shadow-xl transition-all duration-300 flex flex-col justify-between p-4">
                    <!-- Status Ring when speaking -->
                    <div id="border-user" class="speaking-border absolute inset-0 border-4 border-emerald-400 rounded-2xl opacity-0 pointer-events-none transition-opacity duration-300 z-10"></div>
                    
                    <!-- Simulated Camera Preview / Off state -->
                    <video id="userCamVideo" class="hidden absolute inset-0 w-full h-full object-cover rounded-2xl" autoplay muted playsinline></video>
                    
                    <div class="flex justify-between items-start z-10">
                        <div class="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-emerald-500/30">
                            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                            <span class="text-xs font-semibold text-emerald-200">Você</span>
                            <span class="text-[10px] text-slate-400 font-normal">| Host</span>
                        </div>
                        <div id="handRaisedBadge" class="hidden bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2.5 py-0.5 rounded-full text-xs font-semibold animate-bounce">
                            ✋ Mão Levantada
                        </div>
                    </div>

                    <!-- User Avatar (shows when camera is off) -->
                    <div id="userAvatarContainer" class="absolute inset-0 flex items-center justify-center">
                        <div class="relative">
                            <div class="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-emerald-600 via-teal-600 to-cyan-500 p-1 avatar-glow-user transition-transform duration-300 group-hover:scale-105 flex items-center justify-center">
                                <div class="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden">
                                    <i class="fa-solid fa-user text-4xl text-emerald-400"></i>
                                </div>
                            </div>
                            <div id="wave-user" class="hidden absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-end justify-center gap-1 h-6 px-3 py-1 bg-slate-900/90 rounded-full border border-emerald-500/40">
                                <span class="w-1 bg-emerald-400 rounded-full animate-sound-wave" style="animation-delay: 0.1s"></span>
                                <span class="w-1 bg-emerald-400 rounded-full animate-sound-wave" style="animation-delay: 0.3s"></span>
                                <span class="w-1 bg-emerald-400 rounded-full animate-sound-wave" style="animation-delay: 0.2s"></span>
                                <span class="w-1 bg-emerald-400 rounded-full animate-sound-wave" style="animation-delay: 0.4s"></span>
                            </div>
                        </div>
                    </div>

                    <div class="flex justify-between items-end z-10">
                        <span class="text-xs font-medium text-slate-300 bg-slate-900/60 px-2.5 py-1 rounded-md backdrop-blur-sm">
                            <i id="userMicIconStatus" class="fa-solid fa-microphone text-emerald-400 mr-1.5"></i>Você (Líder)
                        </span>
                        <span class="text-[11px] text-slate-400 bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700/50">
                            Audio HD
                        </span>
                    </div>
                </div>

            </div>

            <!-- Debate Action Banner (Floating Controls for AI Discussion) -->
            <div class="max-w-xl mx-auto w-full mt-4 bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-3 flex items-center justify-between gap-3 shadow-2xl">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                        <i class="fa-solid fa-comments font-bold"></i>
                    </div>
                    <div>
                        <h4 class="text-xs font-semibold text-slate-200">Mesa Redonda Interativa</h4>
                        <p class="text-[11px] text-slate-400">Os agentes simulam um debate estratégico em tempo real.</p>
                    </div>
                </div>
                <button onclick="startAIDebate()" class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-500/25 transition active:scale-95 flex items-center gap-2 whitespace-nowrap">
                    <i class="fa-solid fa-play"></i> Iniciar Debate
                </button>
            </div>

        </main>

        <!-- Right Sidebar: Transcripts & Live Feed -->
        <aside id="sidebar" class="w-80 md:w-96 border-l border-slate-800 bg-slate-900/95 backdrop-blur-md flex flex-col transition-all duration-300 z-20">
            <!-- Sidebar Header -->
            <div class="p-4 border-b border-slate-800 flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <i class="fa-solid fa-list-check text-indigo-400 text-sm"></i>
                    <h3 class="font-semibold text-sm text-slate-200">Transcrição & Logs</h3>
                </div>
                <button onclick="toggleSidebar()" class="text-slate-400 hover:text-white p-1 rounded">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>

            <!-- Messages / Transcriptions Feed -->
            <div id="transcriptFeed" class="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
                
                <!-- Welcome Notice -->
                <div class="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-3 text-slate-300">
                    <div class="flex items-center gap-2 font-semibold text-indigo-300 mb-1">
                        <i class="fa-solid fa-circle-info"></i>
                        <span>Sala Conectada</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed text-[11px]">
                        Bem-vindo à sala de conferência do Nexus Core. Fale no microfone ou clique em "Falar" em um dos agentes para ver a transcrição em tempo real.
                    </p>
                </div>

            </div>

            <!-- Bottom Chat Input Box -->
            <div class="p-3 border-t border-slate-800 bg-slate-950/60">
                <form id="chatForm" onsubmit="handleSendText(event)" class="flex gap-2">
                    <input type="text" id="chatInput" placeholder="Envie uma instrução para os agentes..." class="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition">
                    <button type="submit" class="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition flex items-center justify-center">
                        <i class="fa-solid fa-paper-plane text-xs"></i>
                    </button>
                </form>
            </div>
        </aside>

    </div>

    <!-- Bottom Controls Toolbar (Google Meet Style) -->
    <footer class="h-20 border-t border-slate-800/80 bg-slate-950 px-4 flex items-center justify-between z-30">
        
        <!-- Left Section: Room Info -->
        <div class="hidden md:flex items-center space-x-3 w-1/4">
            <span class="text-xs font-semibold text-slate-300 tracking-wide">Nexus AI Meeting</span>
            <span class="text-slate-600">|</span>
            <span id="activeSpeakerText" class="text-xs text-cyan-400 font-medium truncate">Aguardando participantes...</span>
        </div>

        <!-- Center Controls Bar -->
        <div class="flex items-center justify-center space-x-3 mx-auto">
            
            <!-- Mic Toggle Button -->
            <button id="micBtn" onclick="toggleMic()" class="w-12 h-12 rounded-full bg-slate-800 hover:bg-slate-700 text-white flex items-center justify-center transition shadow-lg border border-slate-700/60 group relative" title="Ativar/Desativar Microfone">
                <i id="micIcon" class="fa-solid fa-microphone text-slate-200 text-base"></i>
                <span class="absolute -top-9 scale-0 group-hover:scale-100 transition bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">Microfone</span>
            </button>

            <!-- Camera Toggle Button -->
            <button id="camBtn" onclick="toggleCam()" class="w-12 h-12 rounded-full bg-slate-800 hover:bg-slate-700 text-white flex items-center justify-center transition shadow-lg border border-slate-700/60 group relative" title="Ligar/Desligar Câmera">
                <i id="camIcon" class="fa-solid fa-video-slash text-slate-400 text-base"></i>
                <span class="absolute -top-9 scale-0 group-hover:scale-100 transition bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">Câmera</span>
            </button>

            <!-- Raise Hand Button -->
            <button id="handBtn" onclick="toggleHand()" class="w-12 h-12 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center transition shadow-lg border border-slate-700/60 group relative" title="Levantar a Mão">
                <i id="handIcon" class="fa-regular fa-hand text-base"></i>
                <span class="absolute -top-9 scale-0 group-hover:scale-100 transition bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">Levantar Mão</span>
            </button>

            <!-- Share Screen Button -->
            <button id="screenBtn" onclick="toggleScreenShare()" class="w-12 h-12 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center transition shadow-lg border border-slate-700/60 group relative" title="Compartilhar Tela">
                <i class="fa-solid fa-desktop text-base"></i>
                <span class="absolute -top-9 scale-0 group-hover:scale-100 transition bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">Compartilhar Tela</span>
            </button>

            <!-- End Call Button -->
            <button onclick="leaveMeeting()" class="w-14 h-12 rounded-full bg-rose-600 hover:bg-rose-700 text-white flex items-center justify-center transition shadow-lg shadow-rose-600/30 group relative" title="Sair da Chamada">
                <i class="fa-solid fa-phone-slash text-lg"></i>
                <span class="absolute -top-9 scale-0 group-hover:scale-100 transition bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">Encerrar</span>
            </button>
        </div>

        <!-- Right Side Utility Controls -->
        <div class="hidden md:flex items-center justify-end space-x-2 w-1/4">
            <button onclick="toggleGridDensity()" class="p-2.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition text-xs flex items-center gap-1.5" title="Mudar Visualização">
                <i class="fa-solid fa-border-all"></i>
                <span>Grid</span>
            </button>
        </div>

    </footer>

    <!-- JavaScript Application Logic -->
    <script>
        // --- State Management ---
        let state = {
            micActive: false,
            camActive: false,
            handRaised: false,
            screenSharing: false,
            sidebarOpen: true,
            activeSpeaker: null,
            debateInProgress: false
        };

        // --- Agent Preset Speeches ---
        const AGENT_DATA = {
            atlas: {
                name: "Atlas",
                title: "Arquiteto de Software",
                color: "cyan",
                badgeBg: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
                speeches: [
                    "Analisei a arquitetura do Nexus Core. Recomendo utilizarmos microsserviços orientados a eventos para garantir baixíssima latência.",
                    "Precisamos otimizar a carga da API do Gemini e do Claude utilizando um Gateway de Cache Redis inteligente.",
                    "A infraestrutura no Render está estável. Podemos aplicar auto-scaling para suportar o pico de conexões simultâneas."
                ]
            },
            lyra: {
                name: "Lyra",
                title: "Estrategista de Marketing",
                color: "purple",
                badgeBg: "bg-purple-500/20 text-purple-300 border-purple-500/30",
                speeches: [
                    "Do ponto de vista do usuário, essa interface estilo sala de conferência aumenta o engajamento em 40%!",
                    "Podemos promover esse painel interativo como a nova era de reuniões corporativas assistidas por Inteligência Artificial.",
                    "Sugiro incluir uma opção de exportar o resumo da reunião automaticamente em PDF ao final da chamada."
                ]
            },
            chronos: {
                name: "Chronos",
                title: "Gestor de Riscos e Finanças",
                color: "amber",
                badgeBg: "bg-amber-500/20 text-amber-300 border-amber-500/30",
                speeches: [
                    "Atenção ao consumo de tokens das requisições! Recomendo limitar o orçamento mensal por cliente.",
                    "Do ponto de vista de conformidade e LGPD, a criptografia ponta a ponta dos dados de áudio é mandatória.",
                    "Calculando o ROI desta implementação: a redução no tempo de tomada de decisões compensa o investimento em infraestrutura."
                ]
            }
        };

        // --- Clock Functionality ---
        function updateClock() {
            const now = new Date();
            const hrs = String(now.getHours()).padStart(2, '0');
            const mins = String(now.getMinutes()).padStart(2, '0');
            document.getElementById('clockDisplay').textContent = `${hrs}:${mins}`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // --- Sidebar Controls ---
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            state.sidebarOpen = !state.sidebarOpen;
            if (state.sidebarOpen) {
                sidebar.classList.remove('-mr-80', 'md:-mr-96', 'hidden');
                document.getElementById('unreadBadge').classList.add('hidden');
            } else {
                sidebar.classList.add('hidden');
            }
        }

        // --- Speaking Visualization ---
        function setSpeaker(speakerId, textContent = "") {
            // Reset previous speaker styling
            ['atlas', 'lyra', 'chronos', 'user'].forEach(id => {
                const card = document.getElementById(`card-${id}`);
                const border = card.querySelector('.speaking-border');
                const wave = document.getElementById(`wave-${id}`);
                
                if (border) border.classList.add('opacity-0');
                if (wave) wave.classList.add('hidden');
            });

            if (!speakerId) {
                state.activeSpeaker = null;
                document.getElementById('activeSpeakerText').textContent = "Aguardando participantes...";
                return;
            }

            state.activeSpeaker = speakerId;
            const targetCard = document.getElementById(`card-${speakerId}`);
            const targetBorder = targetCard.querySelector('.speaking-border');
            const targetWave = document.getElementById(`wave-${speakerId}`);

            if (targetBorder) targetBorder.classList.remove('opacity-0');
            if (targetWave) targetWave.classList.remove('hidden');

            const name = speakerId === 'user' ? 'Você' : AGENT_DATA[speakerId]?.name;
            document.getElementById('activeSpeakerText').textContent = `${name} está falando...`;

            // If there's text content, push to transcript
            if (textContent) {
                appendTranscript(speakerId, textContent);
            }
        }

        // --- Speech Trigger for Single Agent ---
        function triggerAgentSpeech(agentKey) {
            const agent = AGENT_DATA[agentKey];
            if (!agent) return;

            const randomSpeech = agent.speeches[Math.floor(Math.random() * agent.speeches.length)];
            setSpeaker(agentKey, randomSpeech);

            // Simulate TTS voice / speaking duration
            setTimeout(() => {
                setSpeaker(null);
            }, 4500);
        }

        // --- Transcript Feed Management ---
        function appendTranscript(speakerId, text) {
            const feed = document.getElementById('transcriptFeed');
            const isUser = speakerId === 'user';
            const agent = AGENT_DATA[speakerId];

            const now = new Date();
            const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

            const name = isUser ? 'Você' : agent.name;
            const badgeBg = isUser ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : agent.badgeBg;
            const icon = isUser ? 'fa-user text-emerald-400' : 'fa-robot';

            const itemHTML = `
                <div class="space-y-1.5 animate-fadeIn">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-1.5">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold border ${badgeBg} flex items-center gap-1">
                                <i class="fa-solid ${icon}"></i>
                                ${name}
                            </span>
                        </div>
                        <span class="text-[10px] text-slate-500">${timeStr}</span>
                    </div>
                    <div class="bg-slate-800/70 border border-slate-700/50 rounded-xl p-3 text-slate-200 leading-relaxed">
                        ${text}
                    </div>
                </div>
            `;

            feed.insertAdjacentHTML('beforeend', itemHTML);
            feed.scrollTop = feed.scrollHeight;

            // Notify if sidebar is closed
            if (!state.sidebarOpen) {
                document.getElementById('unreadBadge').classList.remove('hidden');
            }
        }

        // --- Interactive AI Debate Simulator ---
        async function startAIDebate() {
            if (state.debateInProgress) return;
            state.debateInProgress = true;

            const debateSteps = [
                { id: 'atlas', text: "Colegas, proponho utilizarmos uma arquitetura descentralizada para a nova versão do Nexus Core." },
                { id: 'chronos', text: "Atlas, essa descentralização aumentará os custos operacionais em quase 35%. Qual a justificativa financeira?" },
                { id: 'lyra', text: "Vejam pelo lado do marketing: um sistema ultra-rápido e descentralizado atrairá grandes clientes corporativos imediatamente!" },
                { id: 'atlas', text: "Exato Lyra! A escalabilidade horizontal compensará os custos iniciais apontados pelo Chronos." },
                { id: 'chronos', text: "Se garantirmos um ROI positivo em até 6 meses, dou meu aval financeiro para o projeto." }
            ];

            for (const step of debateSteps) {
                setSpeaker(step.id, step.text);
                await new Promise(resolve => setTimeout(resolve, 4000));
            }

            setSpeaker(null);
            state.debateInProgress = false;
        }

        // --- Mic Controls & Real Speech Detection (Web Speech API) ---
        let recognition = null;

        function toggleMic() {
            state.micActive = !state.micActive;
            const micBtn = document.getElementById('micBtn');
            const micIcon = document.getElementById('micIcon');
            const userMicStatus = document.getElementById('userMicIconStatus');

            if (state.micActive) {
                micBtn.classList.remove('bg-slate-800', 'hover:bg-slate-700');
                micBtn.classList.add('bg-emerald-600', 'hover:bg-emerald-500');
                micIcon.className = "fa-solid fa-microphone text-white text-base";
                userMicStatus.className = "fa-solid fa-microphone text-emerald-400 mr-1.5";

                startVoiceRecognition();
            } else {
                micBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
                micBtn.classList.add('bg-slate-800', 'hover:bg-slate-700');
                micIcon.className = "fa-solid fa-microphone-slash text-rose-400 text-base";
                userMicStatus.className = "fa-solid fa-microphone-slash text-rose-400 mr-1.5";

                stopVoiceRecognition();
                setSpeaker(null);
            }
        }

        function startVoiceRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.lang = 'pt-BR';

                recognition.onstart = () => {
                    setSpeaker('user');
                };

                recognition.onresult = (event) => {
                    const lastResultIndex = event.results.length - 1;
                    const transcript = event.results[lastResultIndex][0].transcript;
                    appendTranscript('user', transcript);
                };

                recognition.onerror = () => {
                    setSpeaker(null);
                };

                recognition.onend = () => {
                    if (state.micActive) {
                        try { recognition.start(); } catch(e){}
                    }
                };

                try { recognition.start(); } catch(e){}
            } else {
                // Fallback simulation if Speech API not supported
                setSpeaker('user', "Simulação de fala ativada no microfone.");
                setTimeout(() => setSpeaker(null), 3000);
            }
        }

        function stopVoiceRecognition() {
            if (recognition) {
                try { recognition.stop(); } catch(e){}
            }
        }

        // --- Camera Toggle ---
        async function toggleCam() {
            state.camActive = !state.camActive;
            const camBtn = document.getElementById('camBtn');
            const camIcon = document.getElementById('camIcon');
            const videoEl = document.getElementById('userCamVideo');
            const avatarContainer = document.getElementById('userAvatarContainer');

            if (state.camActive) {
                camBtn.classList.remove('bg-slate-800', 'hover:bg-slate-700');
                camBtn.classList.add('bg-emerald-600', 'hover:bg-emerald-500');
                camIcon.className = "fa-solid fa-video text-white text-base";

                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                    videoEl.srcObject = stream;
                    videoEl.classList.remove('hidden');
                    avatarContainer.classList.add('hidden');
                } catch (err) {
                    // If webcam fails or permission denied
                    alert("Não foi possível acessar a câmera do dispositivo.");
                    state.camActive = false;
                    camBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
                    camBtn.classList.add('bg-slate-800', 'hover:bg-slate-700');
                    camIcon.className = "fa-solid fa-video-slash text-slate-400 text-base";
                }
            } else {
                camBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
                camBtn.classList.add('bg-slate-800', 'hover:bg-slate-700');
                camIcon.className = "fa-solid fa-video-slash text-slate-400 text-base";

                if (videoEl.srcObject) {
                    const tracks = videoEl.srcObject.getTracks();
                    tracks.forEach(track => track.stop());
                }
                videoEl.classList.add('hidden');
                avatarContainer.classList.remove('hidden');
            }
        }

        // --- Raise Hand Toggle ---
        function toggleHand() {
            state.handRaised = !state.handRaised;
            const handBtn = document.getElementById('handBtn');
            const badge = document.getElementById('handRaisedBadge');

            if (state.handRaised) {
                handBtn.classList.add('bg-amber-600', 'text-white');
                badge.classList.remove('hidden');
                appendTranscript('user', "✋ [Mão Levantada para intervir]");
            } else {
                handBtn.classList.remove('bg-amber-600', 'text-white');
                badge.classList.add('hidden');
            }
        }

        // --- Share Screen Toggle ---
        function toggleScreenShare() {
            state.screenSharing = !state.screenSharing;
            const screenBtn = document.getElementById('screenBtn');
            if (state.screenSharing) {
                screenBtn.classList.add('bg-indigo-600', 'text-white');
                appendTranscript('user', "💻 Iniciou o compartilhamento de tela.");
            } else {
                screenBtn.classList.remove('bg-indigo-600', 'text-white');
            }
        }

        // --- Chat Form Handling ---
        function handleSendText(e) {
            e.preventDefault();
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;

            appendTranscript('user', text);
            input.value = '';

            // Simulate Agent Quick Reaction
            setTimeout(() => {
                triggerAgentSpeech('atlas');
            }, 1200);
        }

        // --- Copy Link ---
        function copyRoomLink() {
            const dummy = document.createElement('input');
            document.body.appendChild(dummy);
            dummy.value = window.location.href;
            dummy.select();
            document.execCommand('copy');
            document.body.removeChild(dummy);
            alert("Link da Sala Nexus Core copiado!");
        }

        // --- Leave Meeting ---
        function leaveMeeting() {
            if (confirm("Deseja realmente sair da Sala de Conferência do Nexus Core?")) {
                document.body.innerHTML = `
                    <div class="h-full flex flex-col items-center justify-center bg-slate-950 text-slate-200 p-6 text-center">
                        <div class="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-4">
                            <i class="fa-solid fa-phone-slash text-2xl text-rose-500"></i>
                        </div>
                        <h2 class="text-xl font-bold mb-2">Você saiu da chamada</h2>
                        <p class="text-sm text-slate-400 mb-6">A conferência do Nexus Core continua ativa em segundo plano.</p>
                        <button onclick="window.location.reload()" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition">
                            Reconectar à Sala
                        </button>
                    </div>
                `;
            }
        }
    </script>
</body>
</html>
